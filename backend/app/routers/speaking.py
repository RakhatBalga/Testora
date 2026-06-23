from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.speaking import SpeakingTask, SpeakingSubmission
from app.models.user import User
from app.schemas.speaking import (
    SpeakingSubmissionOut,
    SpeakingSubmissionSummary,
    SpeakingTaskOut,
)
from app.services.ai import get_speaking_grader
from app.services.mistakes import record_mistakes

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "audio_submissions"
ALLOWED_EXTENSIONS = {".webm", ".ogg", ".mp3", ".wav", ".m4a"}


def _questions(task: SpeakingTask) -> list[str]:
    return [str(q) for q in task.questions or []]


def _safe_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in ALLOWED_EXTENSIONS else ".webm"


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
def submit(
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

    with audio_path.open("wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    audio_url = f"/static/audio_submissions/{filename}"
    submission = SpeakingSubmission(
        user_id=current_user.id,
        task_id=task.id,
        audio_url=audio_url,
        transcript=None,
    )

    grader = get_speaking_grader()
    feedback = grader.grade(
        part=task.part,
        questions=_questions(task),
        audio_path=str(audio_path),
        transcript=None,
    )
    submission.band = feedback.band
    submission.feedback = feedback.to_dict()

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
            "audio_url": s.audio_url,
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
        "audio_url": submission.audio_url,
        "transcript": submission.transcript,
        "band": submission.band,
        "feedback": submission.feedback,
        "created_at": submission.created_at,
    }
