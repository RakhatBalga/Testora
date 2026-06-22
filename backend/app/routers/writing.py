import re
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

router = APIRouter()


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


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
def submit(
    payload: WritingSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(WritingTask).filter(WritingTask.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    word_count = _count_words(payload.text)
    submission = WritingSubmission(
        user_id=current_user.id,
        task_id=task.id,
        text=payload.text,
        word_count=word_count,
        status="pending",
    )

    # Grade via the AI layer (mock now, Claude when AI_PROVIDER=claude).
    grader = get_writing_grader()
    feedback = grader.grade(
        task_type=task.task_type,
        prompt=task.prompt,
        text=payload.text,
        min_words=task.min_words,
    )
    submission.band = feedback.band
    submission.feedback = feedback.to_dict()
    submission.status = "graded"

    db.add(submission)
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
