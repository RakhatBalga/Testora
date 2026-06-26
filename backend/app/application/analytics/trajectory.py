"""Band Trajectory engine.

Overall band over time, reconstructed from real graded events (Writing/Speaking
submissions + Reading/Listening attempts). No AI: each point is the running mean
of the latest known band per skill as of that moment, rounded to the nearest 0.5
— the same definition the Band Gap engine uses for "current", just walked forward
through history. Feeds the dashboard trajectory chart.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.attempt import Attempt
from app.domain.models.test import Test
from app.domain.band import round_ielts as _round_half


def _graded_events(db: Session, user_id: int) -> list[tuple[datetime, str, float]]:
    """All graded events as (created_at, skill, band), oldest first."""
    events: list[tuple[datetime, str, float]] = []

    for skill, model in (("writing", WritingSubmission), ("speaking", SpeakingSubmission)):
        rows = (
            db.query(model.created_at, model.band)
            .filter(model.user_id == user_id, model.band.isnot(None), model.band > 0)
            .all()
        )
        events.extend((created_at, skill, float(band)) for created_at, band in rows)

    for skill in ("reading", "listening"):
        rows = (
            db.query(Attempt.created_at, Attempt.band)
            .join(Test, Attempt.test_id == Test.id)
            .filter(
                Attempt.user_id == user_id,
                Test.test_type == skill,
                Attempt.band.isnot(None),
                Attempt.band > 0,
            )
            .all()
        )
        events.extend((created_at, skill, float(band)) for created_at, band in rows)

    events.sort(key=lambda e: e[0])
    return events


def compute_band_trajectory(db: Session, user_id: int) -> dict:
    """Running overall-band estimate, one point per graded event (oldest first)."""
    events = _graded_events(db, user_id)
    if not events:
        return {"points": [], "delta": None, "has_data": False}

    latest: dict[str, float] = {}
    points: list[dict] = []
    for created_at, skill, band in events:
        latest[skill] = band
        overall = _round_half(sum(latest.values()) / len(latest))
        points.append({"label": created_at.strftime("%b %-d"), "band": overall})

    delta = round(points[-1]["band"] - points[0]["band"], 1)
    return {"points": points, "delta": delta, "has_data": True}
