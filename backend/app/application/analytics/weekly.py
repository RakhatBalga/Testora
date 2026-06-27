"""Seven-day skill signal for the dashboard."""
from datetime import datetime, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from app.domain.band import round_ielts
from app.domain.models.attempt import Attempt
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.test import Test
from app.domain.models.writing import WritingSubmission


def compute_weekly_weakest(db: Session, user_id: int, days: int = 7) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    samples: dict[str, list[float]] = {}

    for skill, model in (("writing", WritingSubmission), ("speaking", SpeakingSubmission)):
        rows = (
            db.query(model.band)
            .filter(
                model.user_id == user_id,
                model.created_at >= since,
                model.band.isnot(None),
                model.band > 0,
            )
            .all()
        )
        if rows:
            samples[skill] = [float(row[0]) for row in rows]

    for skill in ("reading", "listening"):
        rows = (
            db.query(Attempt.band)
            .join(Test, Attempt.test_id == Test.id)
            .filter(
                Attempt.user_id == user_id,
                Attempt.created_at >= since,
                Attempt.band.isnot(None),
                Attempt.band > 0,
                Test.test_type == skill,
            )
            .all()
        )
        if rows:
            samples[skill] = [float(row[0]) for row in rows]

    if not samples:
        return {"has_data": False, "skill": None, "band": None, "attempts": 0, "days": days}

    averages = {skill: round_ielts(mean(values)) for skill, values in samples.items()}
    skill = min(averages, key=lambda key: (averages[key], -len(samples[key]), key))
    return {
        "has_data": True,
        "skill": skill,
        "band": averages[skill],
        "attempts": len(samples[skill]),
        "days": days,
    }
