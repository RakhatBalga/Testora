import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.domain.models.writing import WritingTask, WritingSubmission
from app.domain.models.user import User
from app.api.schemas.writing import (
    WritingTaskOut,
    WritingSubmitIn,
    WritingSubmissionOut,
    WritingSubmissionSummary,
)
from app.infrastructure.ai import get_writing_grader
from app.infrastructure.ai.concurrency import run_grading
from app.application.mistakes import clear_mistakes, record_mistakes
from app.application.writing_precheck import (
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

    submission = await _grade_and_persist(submission, task, db, current_user)
    return _to_out(submission, task)


async def _grade_and_persist(
    submission: WritingSubmission,
    task: WritingTask,
    db: Session,
    current_user: User,
) -> WritingSubmission:
    precheck = validate_writing_submission(
        task_type=task.task_type,
        text=submission.text,
        min_words=task.min_words,
    )
    word_count = precheck.word_count
    submission.word_count = word_count
    submission.status = "pending"
    submission.band = None

    if precheck.valid:
        # Grade via the AI layer (mock now, Gemini when AI_PROVIDER=gemini). The
        # blocking call is offloaded to the threadpool and globally rate-bounded so
        # concurrent gradings can't starve the event loop or hammer the model.
        grader = get_writing_grader()
        feedback = await run_grading(
            grader.grade,
            task_type=task.task_type,
            prompt=task.prompt,
            text=submission.text,
            min_words=task.min_words,
        )
    else:
        feedback = zero_band_feedback(task.task_type, precheck)

    db.add(submission)
    db.flush()  # assign submission.id before replacing/recording its mistakes
    clear_mistakes(
        db,
        user_id=current_user.id,
        submission_id=submission.id,
        skill="writing",
    )
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
        db.commit()
        db.refresh(submission)
        return submission

    submission.band = feedback.band
    submission.status = "graded"

    # Best-effort "Better Version" rewrite (Gemini only; mock returns None so the
    # UI keeps its deterministic diff). A failure here must not fail the grade.
    try:
        improved = await run_grading(
            get_writing_grader().improve,
            task_type=task.task_type,
            prompt=task.prompt,
            text=submission.text,
        )
        if improved:
            submission.improved_text = improved
    except Exception:  # noqa: BLE001
        logger.warning(
            "Better Version generation failed for submission %s", submission.id
        )

    record_mistakes(
        db,
        user_id=current_user.id,
        submission_id=submission.id,
        skill="writing",
        mistakes=feedback.mistakes,
    )
    db.commit()
    db.refresh(submission)
    return submission


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


@router.post("/submissions/{submission_id}/retry", response_model=WritingSubmissionOut)
async def retry_submission(
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
    if sub.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed writing submissions can be retried",
        )

    sub = await _grade_and_persist(sub, sub.task, db, current_user)
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
        "improved_text": sub.improved_text,
        "created_at": sub.created_at,
    }
