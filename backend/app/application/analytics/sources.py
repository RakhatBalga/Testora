"""Shared read helpers over graded submissions.

Bridges the three submission tables (writing_submissions, speaking_submissions,
attempts) into a uniform per-skill view for the analytics engines.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.test import Question, Test
from app.domain.band import round_ielts as _round_half

SKILLS = ("writing", "speaking", "reading", "listening")


def _attempt_query(db: Session, user_id: int, test_type: str):
    return (
        db.query(Attempt)
        .join(Test, Attempt.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type == test_type)
    )


def graded_writing(db: Session, user_id: int):
    """Writing submissions that really were graded (not failed, pending or Band-0 rejected)."""
    return db.query(WritingSubmission).filter(
        WritingSubmission.user_id == user_id,
        WritingSubmission.status == "graded",
        WritingSubmission.band > 0,
    )


def graded_speaking(db: Session, user_id: int):
    return db.query(SpeakingSubmission).filter(SpeakingSubmission.user_id == user_id, SpeakingSubmission.band > 0)


@dataclass(frozen=True)
class ObjectiveMistake:
    """One weak question group in one Reading/Listening attempt.

    Shaped like a `Mistake` row for the weakness engines. These are derived from
    `answer_records` at read time, never stored: the notebook lists the same
    wrong answers one by one, so storing them would count them twice.
    """

    skill: str
    category: str
    subskill: str
    severity: int
    submission_id: int
    created_at: datetime | None


def objective_category(skill: str, question_type: str, question_metadata: dict | None) -> str:
    """The notebook's grouping: question type for Reading, target skill for Listening."""
    if skill == "listening":
        return (question_metadata or {}).get("target_skill") or question_type
    return question_type


def _objective_severity(wrong: int, total: int) -> int:
    """1..3 like graded mistakes: most of the group wrong = 3, a third or more = 2."""
    share = wrong / total
    return 3 if share >= 2 / 3 else 2 if share >= 1 / 3 else 1


def objective_mistakes(
    db: Session, user_id: int, skill: str | None = None, attempt_ids: list[int] | None = None
) -> list[ObjectiveMistake]:
    """Wrong Reading/Listening answers as one item per (attempt, question group).

    Grouping per attempt keeps the scale comparable with Writing, where a review
    yields a handful of mistakes: a 40-question test must not outweigh an essay.
    """
    query = (
        db.query(
            Attempt.id,
            Attempt.created_at,
            Test.test_type,
            Question.question_type,
            Question.question_metadata,
            AnswerRecord.is_correct,
        )
        .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
        .join(Question, AnswerRecord.question_id == Question.id)
        .join(Test, Attempt.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type.in_([skill] if skill else ["reading", "listening"]))
    )
    if attempt_ids is not None:
        query = query.filter(Attempt.id.in_(attempt_ids))

    counts: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])  # [wrong, total]
    created: dict[int, datetime | None] = {}
    for attempt_id, created_at, test_type, question_type, metadata, is_correct in query.all():
        created[attempt_id] = created_at
        group = counts[(test_type, attempt_id, objective_category(test_type, question_type, metadata))]
        group[0] += not is_correct
        group[1] += 1
    return [
        ObjectiveMistake(
            skill=test_type,
            category=category,
            subskill=category,
            severity=_objective_severity(wrong, total),
            submission_id=attempt_id,
            created_at=created[attempt_id],
        )
        for (test_type, attempt_id, category), (wrong, total) in counts.items()
        if wrong
    ]


def opportunities(db: Session, user_id: int) -> dict[str, int]:
    """How many graded attempts exist per skill (the denominator for weakness scores)."""
    return {
        "writing": graded_writing(db, user_id).count(),
        "speaking": graded_speaking(db, user_id).count(),
        "reading": _attempt_query(db, user_id, "reading").count(),
        "listening": _attempt_query(db, user_id, "listening").count(),
    }


def recent_submission_ids(db: Session, user_id: int, skill: str, limit: int = 8) -> list[int]:
    """IDs of the most recent attempts for a skill (newest first)."""
    if skill == "writing":
        rows = (
            graded_writing(db, user_id)
            .with_entities(WritingSubmission.id)
            .order_by(WritingSubmission.created_at.desc())
            .limit(limit)
            .all()
        )
    elif skill == "speaking":
        rows = (
            graded_speaking(db, user_id)
            .with_entities(SpeakingSubmission.id)
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
