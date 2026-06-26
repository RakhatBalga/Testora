"""Shared read helpers over graded submissions.

Bridges the three submission tables (writing_submissions, speaking_submissions,
attempts) into a uniform per-skill view for the analytics engines.
"""
from statistics import mean

from sqlalchemy.orm import Session

from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.attempt import Attempt
from app.domain.models.test import Test
from app.domain.band import round_ielts as _round_half

SKILLS = ("writing", "speaking", "reading", "listening")


def _attempt_query(db: Session, user_id: int, test_type: str):
    return (
        db.query(Attempt)
        .join(Test, Attempt.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type == test_type)
    )


def opportunities(db: Session, user_id: int) -> dict[str, int]:
    """How many graded attempts exist per skill (the denominator for weakness scores)."""
    return {
        "writing": db.query(WritingSubmission).filter(WritingSubmission.user_id == user_id).count(),
        "speaking": db.query(SpeakingSubmission).filter(SpeakingSubmission.user_id == user_id).count(),
        "reading": _attempt_query(db, user_id, "reading").count(),
        "listening": _attempt_query(db, user_id, "listening").count(),
    }


def recent_submission_ids(db: Session, user_id: int, skill: str, limit: int = 8) -> list[int]:
    """IDs of the most recent attempts for a skill (newest first)."""
    if skill == "writing":
        rows = (
            db.query(WritingSubmission.id)
            .filter(WritingSubmission.user_id == user_id)
            .order_by(WritingSubmission.created_at.desc())
            .limit(limit)
            .all()
        )
    elif skill == "speaking":
        rows = (
            db.query(SpeakingSubmission.id)
            .filter(SpeakingSubmission.user_id == user_id)
            .order_by(SpeakingSubmission.created_at.desc())
            .limit(limit)
            .all()
        )
    elif skill in ("reading", "listening"):
        rows = (
            _attempt_query(db, user_id, skill)
            .order_by(Attempt.created_at.desc())
            .with_entities(Attempt.id)
            .limit(limit)
            .all()
        )
    else:
        return []
    return [r[0] for r in rows]


def skill_bands(db: Session, user_id: int, window: int = 3) -> dict[str, float]:
    """Current estimated band per skill = mean of the last `window` graded bands."""
    bands: dict[str, float] = {}

    for skill, model in (("writing", WritingSubmission), ("speaking", SpeakingSubmission)):
        rows = (
            db.query(model.band)
            .filter(model.user_id == user_id, model.band.isnot(None), model.band > 0)
            .order_by(model.created_at.desc())
            .limit(window)
            .all()
        )
        vals = [r[0] for r in rows]
        if vals:
            bands[skill] = _round_half(mean(vals))

    for skill in ("reading", "listening"):
        rows = (
            _attempt_query(db, user_id, skill)
            .filter(Attempt.band.isnot(None), Attempt.band > 0)
            .order_by(Attempt.created_at.desc())
            .with_entities(Attempt.band)
            .limit(window)
            .all()
        )
        vals = [r[0] for r in rows]
        if vals:
            bands[skill] = _round_half(mean(vals))

    return bands


def latest_feedback(db: Session, user_id: int, skill: str) -> dict | None:
    """The most recent graded feedback JSON for a Writing/Speaking skill."""
    model = {"writing": WritingSubmission, "speaking": SpeakingSubmission}.get(skill)
    if model is None:
        return None
    row = (
        db.query(model)
        .filter(model.user_id == user_id, model.band.isnot(None), model.band > 0)
        .order_by(model.created_at.desc())
        .first()
    )
    if row is None or not row.feedback:
        return None
    return row.feedback
