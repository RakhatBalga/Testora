"""Practice test catalog: what is published and what a user may see of it."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.attempt import Attempt
from app.domain.models.test import Question, Section, Test
from app.domain.publication import is_published


def list_published_tests(db: Session) -> list[dict]:
    # One grouped query for question counts, so the library can show "N questions"
    # without an N+1 fetch of every test's sections.
    counts = dict(
        db.query(Section.test_id, func.count(Question.id))
        .join(Question, Question.section_id == Section.id)
        .group_by(Section.test_id)
        .all()
    )
    tests = [t for t in db.query(Test).order_by(Test.id).all() if is_published(t)]
    return [
        {
            "id": t.id,
            "title": t.title,
            "test_type": t.test_type,
            "description": t.description,
            "duration_minutes": t.duration_minutes,
            "difficulty": t.difficulty,
            "question_count": counts.get(t.id, 0),
        }
        for t in tests
    ]


def get_published_test(db: Session, test_id: int) -> Test | None:
    test = db.query(Test).filter(Test.id == test_id).first()
    return test if test and is_published(test) else None


def has_attempt(db: Session, user_id: int, test_id: int) -> bool:
    return db.query(Attempt.id).filter(Attempt.user_id == user_id, Attempt.test_id == test_id).first() is not None
