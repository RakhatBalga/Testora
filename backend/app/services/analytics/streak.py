"""Practice streak — consecutive days with at least one graded activity.

Derived from real submission/attempt dates (Writing, Speaking, Reading,
Listening). No mock, no AI. A day counts if any skill was practised on it.
"""
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.writing import WritingSubmission
from app.models.speaking import SpeakingSubmission
from app.models.attempt import Attempt


def _activity_dates(db: Session, user_id: int) -> set:
    dates: set = set()
    for model in (WritingSubmission, SpeakingSubmission):
        rows = (
            db.query(func.date(model.created_at))
            .filter(model.user_id == user_id)
            .distinct()
            .all()
        )
        dates.update(r[0] for r in rows if r[0])
    rows = (
        db.query(func.date(Attempt.created_at))
        .filter(Attempt.user_id == user_id)
        .distinct()
        .all()
    )
    dates.update(r[0] for r in rows if r[0])
    # func.date may return strings on some drivers — normalise to date objects.
    return {datetime.fromisoformat(str(d)).date() if not hasattr(d, "year") else d for d in dates}


def compute_streak(db: Session, user_id: int) -> dict:
    dates = _activity_dates(db, user_id)
    if not dates:
        return {"current_streak": 0, "active_today": False}

    today = datetime.utcnow().date()
    active_today = today in dates

    # Start from today if active, otherwise from yesterday (today still in progress).
    cursor = today if active_today else today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)

    return {"current_streak": streak, "active_today": active_today}
