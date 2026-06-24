"""Analytics endpoints — pure aggregation over stored mistakes/submissions.

No AI calls happen here. Grading writes mistakes; these endpoints only read.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.goal import Goal
from app.models.user import User
from app.services.analytics import (
    compute_weaknesses,
    compute_recurring_mistakes,
    compute_band_gap,
    generate_blockers,
)
from app.services.analytics.band_gap import DEFAULT_TARGET

router = APIRouter()


def _resolve_target(db: Session, user_id: int, override: float | None) -> float:
    """Use an explicit ?target override, else the user's saved goal, else the default."""
    if override is not None:
        return override
    goal = db.query(Goal).filter(Goal.user_id == user_id).first()
    return goal.target_band if goal and goal.target_band else DEFAULT_TARGET


@router.get("/weaknesses")
def weaknesses(
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"weaknesses": compute_weaknesses(db, current_user.id, limit=limit)}


@router.get("/blockers")
def blockers(
    target: float | None = Query(None, ge=4.0, le=9.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved = _resolve_target(db, current_user.id, target)
    return {"blockers": generate_blockers(db, current_user.id, target=resolved)}


@router.get("/band-gap")
def band_gap(
    target: float | None = Query(None, ge=4.0, le=9.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = db.query(Goal).filter(Goal.user_id == current_user.id).first()
    resolved = _resolve_target(db, current_user.id, target)
    return compute_band_gap(
        db,
        current_user.id,
        target=resolved,
        exam_date=goal.exam_date if goal else None,
        current_fallback=goal.current_band if goal else None,
    )


@router.get("/recurring-mistakes")
def recurring_mistakes(
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"recurring": compute_recurring_mistakes(db, current_user.id, limit=limit)}
