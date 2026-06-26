"""Practice streak — consecutive days with at least one graded activity.

Derived from real submission/attempt dates (Writing, Speaking, Reading,
Listening). No mock, no AI. A day counts if any skill was practised on it.
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.infrastructure.time import local_today, to_local_date
from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.attempt import Attempt


def _activity_dates(db: Session, user_id: int) -> set:
    """Distinct local calendar dates the user was active on.

    Dates are derived in the app timezone (not UTC) so a late-evening session in
    a UTC+5/+6 region counts toward the correct local day.
    """
    dates: set = set()
    for model in (WritingSubmission, SpeakingSubmission):
        rows = (
            db.query(model.created_at)
            .filter(model.user_id == user_id, model.created_at.isnot(None))
            .all()
        )
        dates.update(to_local_date(r[0]) for r in rows)
    rows = (
        db.query(Attempt.created_at)
        .filter(Attempt.user_id == user_id, Attempt.created_at.isnot(None))
        .all()
    )
    dates.update(to_local_date(r[0]) for r in rows)
    return dates


def compute_streak(db: Session, user_id: int) -> dict:
    dates = _activity_dates(db, user_id)
    if not dates:
        return {"current_streak": 0, "active_today": False}

    today = local_today()
    active_today = today in dates

    # Start from today if active, otherwise from yesterday (today still in progress).
    cursor = today if active_today else today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)

    return {"current_streak": streak, "active_today": active_today}
