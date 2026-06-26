"""Analytics endpoints — pure aggregation over stored mistakes/submissions.

No AI calls happen here. Grading writes mistakes; these endpoints only read.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.domain.models.user import User
from app.application.analytics import (
    compute_weaknesses,
    compute_recurring_mistakes,
    compute_band_gap,
    compute_band_trajectory,
    compute_progress_impact,
    compute_daily_plan,
    compute_blocker_history,
    compute_streak,
    compute_recommendations,
    generate_blockers,
)
from app.application.analytics.band_gap import DEFAULT_TARGET

router = APIRouter()


def _target_for(current_user: User, requested: float | None) -> float:
    return requested if requested is not None else (current_user.target_band or DEFAULT_TARGET)


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
    return {"blockers": generate_blockers(db, current_user.id, target=_target_for(current_user, target))}


@router.get("/band-gap")
def band_gap(
    target: float | None = Query(None, ge=4.0, le=9.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_band_gap(db, current_user.id, target=_target_for(current_user, target))


@router.get("/band-trajectory")
def band_trajectory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_band_trajectory(db, current_user.id)


@router.get("/streak")
def streak(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_streak(db, current_user.id)


@router.get("/blocker-history")
def blocker_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_blocker_history(db, current_user.id)


@router.get("/daily-plan")
def daily_plan(
    target: float | None = Query(None, ge=4.0, le=9.0),
    limit: int = Query(3, ge=1, le=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_daily_plan(db, current_user.id, target=_target_for(current_user, target), limit=limit)


@router.get("/progress-impact")
def progress_impact(
    skill: str = Query(..., pattern="^(writing|speaking)$"),
    submission_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_progress_impact(db, current_user.id, skill, submission_id)


@router.get("/recommendations")
def recommendations(
    target: float | None = Query(None, ge=4.0, le=9.0),
    limit: int = Query(5, ge=1, le=8),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {
        "recommendations": compute_recommendations(
            db,
            current_user.id,
            target=_target_for(current_user, target),
            limit=limit,
        )
    }


@router.get("/recurring-mistakes")
def recurring_mistakes(
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"recurring": compute_recurring_mistakes(db, current_user.id, limit=limit)}
