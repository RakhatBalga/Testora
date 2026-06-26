"""Persist mistakes produced by the grading layer.

The grader (infrastructure/ai) detects mistakes; this records them. Kept
separate from analytics, which only *reads* these rows.
"""
from sqlalchemy.orm import Session

from app.domain.models.mistake import Mistake
from app.infrastructure.ai.base import MistakeItem


def clear_mistakes(
    db: Session,
    *,
    user_id: int,
    submission_id: int,
    skill: str,
) -> None:
    db.query(Mistake).filter(
        Mistake.user_id == user_id,
        Mistake.submission_id == submission_id,
        Mistake.skill == skill,
    ).delete(synchronize_session=False)


def record_mistakes(
    db: Session,
    *,
    user_id: int,
    submission_id: int,
    skill: str,
    mistakes: list[MistakeItem],
) -> None:
    for m in mistakes:
        db.add(
            Mistake(
                user_id=user_id,
                submission_id=submission_id,
                skill=skill,
                category=m.category,
                subskill=m.subskill,
                severity=max(1, min(3, m.severity)),
                snippet=m.snippet,
                correction=m.correction,
                explanation=m.explanation,
            )
        )
