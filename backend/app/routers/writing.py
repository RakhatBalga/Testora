import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.writing import WritingTask, WritingSubmission
from app.models.user import User
from app.schemas.writing import (
    WritingTaskOut,
    WritingSubmitIn,
    WritingSubmissionOut,
    WritingSubmissionSummary,
)
from app.services.ai import get_writing_grader
from app.services.ai.concurrency import run_grading
from app.services.mistakes import record_mistakes
from app.services.writing_precheck import (
    count_words,
    validate_writing_submission,
    zero_band_feedback,
)

router = APIRouter()
logger = logging.getLogger("testora.writing")


@router.get("/tasks", response_model=List[WritingTaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(WritingTask).order_by(WritingTask.task_type).all()


@router.get("/tasks/{task_id}", response_model=WritingTaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(WritingTask).filter(WritingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/submit", response_model=WritingSubmissionOut)
async def submit(
    payload: WritingSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(WritingTask).filter(WritingTask.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    precheck = validate_writing_submission(
        task_type=task.task_type,
        text=payload.text,
        min_words=task.min_words,
    )
    word_count = precheck.word_count
    submission = WritingSubmission(
        user_id=current_user.id,
        task_id=task.id,
        text=payload.text,
        word_count=word_count,
        status="pending",
    )

    if precheck.valid:
        # Grade via the AI layer (mock now, Gemini when AI_PROVIDER=gemini). The
        # blocking call is offloaded to the threadpool and globally rate-bounded so
        # concurrent gradings can't starve the event loop or hammer the model.
        grader = get_writing_grader()
        feedback = await run_grading(
            grader.grade,
            task_type=task.task_type,
            prompt=task.prompt,
            text=payload.text,
            min_words=task.min_words,
        )
    else:
        feedback = zero_band_feedback(task.task_type, precheck)

    submission.feedback = feedback.to_dict()
    if feedback.error:
        # Grading failed — preserve the user's text but do NOT record a band or
        # mistakes. Analytics ignore failed/unbanded submissions, and the user
        # can re-submit. (Mock graders never set error, so they're unaffected.)
        submission.band = None
        submission.status = "failed"
        logger.warning(
            "Writing grading failed for user %s task %s; saved as failed",
            current_user.id,
            task.id,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return _to_out(submission, task)

    submission.band = feedback.band
    submission.status = "graded"

    db.add(submission)
    db.flush()  # assign submission.id before recording its mistakes
    record_mistakes(
        db,
        user_id=current_user.id,
        submission_id=submission.id,
        skill="writing",
        mistakes=feedback.mistakes,
    )
    db.commit()
    db.refresh(submission)

    return _to_out(submission, task)


@router.get("/submissions", response_model=List[WritingSubmissionSummary])
def list_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subs = (
        db.query(WritingSubmission)
        .filter(WritingSubmission.user_id == current_user.id)
        .order_by(WritingSubmission.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "task_id": s.task_id,
            "task_title": s.task.title,
            "word_count": s.word_count,
            "status": s.status,
            "band": s.band,
            "created_at": s.created_at,
        }
        for s in subs
    ]


@router.get("/submissions/{submission_id}", response_model=WritingSubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = (
        db.query(WritingSubmission)
        .filter(
            WritingSubmission.id == submission_id,
            WritingSubmission.user_id == current_user.id,
        )
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _to_out(sub, sub.task)


def _to_out(sub: WritingSubmission, task: WritingTask) -> dict:
    return {
        "id": sub.id,
        "task_id": sub.task_id,
        "task_title": task.title,
        "task_prompt": task.prompt,
        "text": sub.text,
        "word_count": sub.word_count,
        "status": sub.status,
        "band": sub.band,
        "feedback": sub.feedback,
        "created_at": sub.created_at,
    }
