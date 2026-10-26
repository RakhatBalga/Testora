from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.infrastructure.config import settings
from app.api.dependencies import get_db, get_current_user, user_rate_limit
from app.api.uploads import read_capped
from app.domain.models.speaking import SpeakingTask, SpeakingSubmission
from app.domain.models.user import User
from app.api.schemas.speaking import (
    SpeakingSubmissionOut,
    SpeakingSubmissionSummary,
    SpeakingTaskOut,
)
from app.application import speaking as speaking_service
from app.application.quota import quota_status
from app.infrastructure.storage import storage_for_key

router = APIRouter()


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


@router.get("/quota")
def get_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return quota_status(
        db, SpeakingSubmission, current_user, settings.FREE_SPEAKING_SUBMISSIONS
    )


@router.post(
    "/submit",
    response_model=SpeakingSubmissionOut,
    dependencies=[Depends(user_rate_limit("speaking-submit", 6))],
)
def submit(
    task_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Gate first: a disabled feature must not even read the upload.
    speaking_service.require_speaking_enabled()
    task = db.query(SpeakingTask).filter(SpeakingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = read_capped(audio, settings.MAX_AUDIO_UPLOAD_MB, "Audio")
    submission = speaking_service.submit_speaking(db, current_user, task, data)
    return _to_out(submission, task)


def _resolve_media_user(token: str | None, db: Session) -> User:
    """Authenticate a media request via an Authorization bearer header."""
    cred_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_error
    return get_current_user(token=token, db=db)


@router.get("/submissions/{submission_id}/audio")
def get_audio(
    submission_id: int,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """Stream a recording only to its owner (ownership-checked, never public)."""
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:]
    user = _resolve_media_user(bearer, db)

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
    blob = storage_for_key(submission.audio_url).load(db, submission.audio_url)
    if blob is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return Response(
        content=blob.data,
        media_type=blob.content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


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
        "questions": speaking_service.task_questions(task),
        "audio_url": _audio_endpoint(submission.id),
        "transcript": submission.transcript,
        "band": submission.band,
        "feedback": submission.feedback,
        "created_at": submission.created_at,
    }
