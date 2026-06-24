"""Goal endpoints — the user's target band, exam date, and self-estimate.

Captured at onboarding and read by the band-gap engine (which measures the gap
against ``target_band``) and the dashboard countdown (``exam_date``). One goal
per user; ``POST`` upserts.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalRequest, GoalResponse

router = APIRouter()


@router.get("", response_model=GoalResponse | None)
def get_goal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Goal).filter(Goal.user_id == current_user.id).first()


@router.post("", response_model=GoalResponse)
def save_goal(
    payload: GoalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = db.query(Goal).filter(Goal.user_id == current_user.id).first()
    if goal is None:
        goal = Goal(user_id=current_user.id)
        db.add(goal)
    goal.target_band = payload.target_band
    goal.current_band = payload.current_band
    goal.exam_date = payload.exam_date
    db.commit()
    db.refresh(goal)
    return goal
