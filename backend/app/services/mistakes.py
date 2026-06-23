"""Persist mistakes produced by the grading layer.

The grader (services/ai) detects mistakes; this records them. Kept separate from
analytics, which only *reads* these rows.
"""
from sqlalchemy.orm import Session

from app.models.mistake import Mistake
from app.services.ai.base import MistakeItem


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
