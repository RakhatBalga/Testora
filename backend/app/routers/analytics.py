"""Analytics endpoints — pure aggregation over stored mistakes/submissions.

No AI calls happen here. Grading writes mistakes; these endpoints only read.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.analytics import (
    compute_weaknesses,
    compute_recurring_mistakes,
    compute_band_gap,
    generate_blockers,
)
from app.services.analytics.band_gap import DEFAULT_TARGET

router = APIRouter()


@router.get("/weaknesses")
def weaknesses(
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"weaknesses": compute_weaknesses(db, current_user.id, limit=limit)}


@router.get("/blockers")
def blockers(
    target: float = Query(DEFAULT_TARGET, ge=4.0, le=9.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"blockers": generate_blockers(db, current_user.id, target=target)}


@router.get("/band-gap")
def band_gap(
    target: float = Query(DEFAULT_TARGET, ge=4.0, le=9.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_band_gap(db, current_user.id, target=target)


@router.get("/recurring-mistakes")
def recurring_mistakes(
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"recurring": compute_recurring_mistakes(db, current_user.id, limit=limit)}
