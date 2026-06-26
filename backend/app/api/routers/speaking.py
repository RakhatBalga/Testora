import logging
import mimetypes
from pathlib import Path
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.infrastructure.config import settings
from app.api.dependencies import get_db, get_current_user
from app.domain.models.speaking import SpeakingTask, SpeakingSubmission
from app.domain.models.user import User
from app.api.schemas.speaking import (
    SpeakingSubmissionOut,
    SpeakingSubmissionSummary,
    SpeakingTaskOut,
)
from app.infrastructure.ai import get_speaking_grader
from app.infrastructure.ai.concurrency import run_grading
from app.application.mistakes import record_mistakes

router = APIRouter()
logger = logging.getLogger("testora.speaking")

# Private (NOT publicly served) directory for user recordings — they are PII and
# must only be reachable through the authenticated audio endpoint below. Resolve
# from the backend root (/app in the Docker image) so docker-compose's
# /app/private/audio_submissions volume actually persists uploads.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_DIR = _BACKEND_ROOT / "private" / "audio_submissions"
# Legacy location for recordings created before audio was made private.
_LEGACY_DIR = _BACKEND_ROOT / "static" / "audio_submissions"
ALLOWED_EXTENSIONS = {".webm", ".ogg", ".mp3", ".wav", ".m4a"}
_MAX_AUDIO_BYTES = settings.MAX_AUDIO_UPLOAD_MB * 1024 * 1024
_CHUNK = 1024 * 1024  # 1 MiB


def _questions(task: SpeakingTask) -> list[str]:
    return [str(q) for q in task.questions or []]


def _safe_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in ALLOWED_EXTENSIONS else ".webm"


def _audio_endpoint(submission_id: int) -> str:
    """Authenticated URL the client uses to fetch a recording."""
    return f"/speaking/submissions/{submission_id}/audio"


@router.get("/tasks", response_model=list[SpeakingTaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(SpeakingTask).order_by(SpeakingTask.part, SpeakingTask.id).all()


@router.get("/tasks/{task_id}", response_model=SpeakingTaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(SpeakingTask).filter(SpeakingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/submit", response_model=SpeakingSubmissionOut)
async def submit(
    task_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(SpeakingTask).filter(SpeakingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = _safe_suffix(audio.filename)
    filename = f"user{current_user.id}_task{task.id}_{uuid.uuid4().hex}{suffix}"
    audio_path = UPLOAD_DIR / filename

    # Stream to disk with a hard size ceiling so a huge upload can't exhaust
    # memory/disk or blow up the AI request. Abort and clean up if exceeded.
    written = 0
    try:
        with audio_path.open("wb") as buffer:
            while chunk := audio.file.read(_CHUNK):
                written += len(chunk)
                if written > _MAX_AUDIO_BYTES:
                    buffer.close()
                    audio_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Audio exceeds the {settings.MAX_AUDIO_UPLOAD_MB} MB limit.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    if written == 0:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty audio upload.")

    submission = SpeakingSubmission(
        user_id=current_user.id,
        task_id=task.id,
        # Store only the filename; the file is private and served via an
        # authenticated endpoint, not a public static URL.
        audio_url=filename,
        transcript=None,
    )

    grader = get_speaking_grader()
    feedback = await run_grading(
        grader.grade,
        part=task.part,
        questions=_questions(task),
        audio_path=str(audio_path),
        transcript=None,
    )
    submission.feedback = feedback.to_dict()

    if feedback.error:
        # Grading failed — keep the recording, but don't store a bogus band or
        # mistakes. The user can re-submit.
        submission.band = None
        logger.warning(
            "Speaking grading failed for user %s task %s; saved without a band",
            current_user.id,
            task.id,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return _to_out(submission, task)

    submission.band = feedback.band

    db.add(submission)
    db.flush()  # assign submission.id before recording its mistakes
    record_mistakes(
        db,
        user_id=current_user.id,
        submission_id=submission.id,
        skill="speaking",
        mistakes=feedback.mistakes,
    )
    db.commit()
    db.refresh(submission)

    return _to_out(submission, task)


def _resolve_media_user(token: str | None, db: Session) -> User:
    """Authenticate a media request via a bearer header OR a `token` query param.

    The browser <audio> element can't send an Authorization header, so signed
    playback falls back to a query-string token (the same short-lived JWT).
    """
    cred_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_error
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise cred_error
    except JWTError:
        raise cred_error
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise cred_error
    return user


@router.get("/submissions/{submission_id}/audio")
def get_audio(
    submission_id: int,
    token: str | None = Query(None),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """Stream a recording only to its owner (ownership-checked, private dir)."""
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:]
    user = _resolve_media_user(token or bearer, db)

    submission = (
        db.query(SpeakingSubmission)
        .filter(
            SpeakingSubmission.id == submission_id,
            SpeakingSubmission.user_id == user.id,
        )
        .first()
    )
    if not submission or not submission.audio_url:
        raise HTTPException(status_code=404, detail="Recording not found")

    name = Path(submission.audio_url).name
    path = UPLOAD_DIR / name
    if not path.exists():
        path = _LEGACY_DIR / name  # recordings from before audio was private
    if not path.exists():
        raise HTTPException(status_code=404, detail="Recording not found")

    media_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.get("/submissions", response_model=list[SpeakingSubmissionSummary])
def list_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submissions = (
        db.query(SpeakingSubmission)
        .filter(SpeakingSubmission.user_id == current_user.id)
        .order_by(SpeakingSubmission.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "task_id": s.task_id,
            "task_part": s.task.part,
            "audio_url": _audio_endpoint(s.id),
            "band": s.band,
            "created_at": s.created_at,
        }
        for s in submissions
    ]


@router.get("/submissions/{submission_id}", response_model=SpeakingSubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submission = (
        db.query(SpeakingSubmission)
        .filter(
            SpeakingSubmission.id == submission_id,
            SpeakingSubmission.user_id == current_user.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _to_out(submission, submission.task)


def _to_out(submission: SpeakingSubmission, task: SpeakingTask) -> dict:
    return {
        "id": submission.id,
        "task_id": submission.task_id,
        "task_part": task.part,
        "questions": _questions(task),
        "audio_url": _audio_endpoint(submission.id),
        "transcript": submission.transcript,
        "band": submission.band,
        "feedback": submission.feedback,
        "created_at": submission.created_at,
    }
