from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user, user_rate_limit
from app.domain.models.writing import WritingTask, WritingSubmission
from app.domain.models.user import User
from app.api.schemas.writing import (
    WritingTaskOut,
    WritingSubmitIn,
    WritingSubmissionOut,
    WritingSubmissionSummary,
)
from app.application import writing as writing_service
from app.application.quota import quota_status
from app.infrastructure.config import settings

router = APIRouter()


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


@router.get("/quota")
def get_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return quota_status(
        db, WritingSubmission, current_user, settings.FREE_WRITING_SUBMISSIONS
    )


@router.post(
    "/submit",
    response_model=WritingSubmissionOut,
    dependencies=[Depends(user_rate_limit("writing-submit", 10))],
)
def submit(
    payload: WritingSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Plain `def`: FastAPI runs it in the threadpool, so the synchronous DB work
    # and the blocking grader never stall the event loop.
    task = db.query(WritingTask).filter(WritingTask.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    submission = writing_service.submit_writing(db, current_user, task, payload.text)
    return _to_out(submission, task)


@router.get("/submissions", response_model=List[WritingSubmissionSummary])
def list_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
        for s in writing_service.list_submissions(db, current_user)
    ]


@router.get("/submissions/{submission_id}", response_model=WritingSubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = writing_service.get_owned_submission(db, current_user, submission_id)
    return _to_out(sub, sub.task)


@router.post(
    "/submissions/{submission_id}/retry",
    response_model=WritingSubmissionOut,
    dependencies=[Depends(user_rate_limit("writing-submit", 10))],
)
def retry_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = writing_service.retry_writing(db, current_user, submission_id)
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
