import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routers import writing
from app.domain.models.mistake import Mistake
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure.ai.base import Feedback, MistakeItem
from app.infrastructure.database import Base


class _SuccessfulGrader:
    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        return Feedback(
            band=7.5,
            criteria={
                "Task Response": 7.5,
                "Coherence & Cohesion": 7.5,
                "Lexical Resource": 7.5,
                "Grammatical Range & Accuracy": 7.5,
            },
            summary="Strong response.",
            suggestions=["Make examples more specific."],
            mistakes=[
                MistakeItem(
                    category="grammar",
                    subskill="articles",
                    severity=1,
                    snippet="in the society",
                    correction="in society",
                )
            ],
            why_not_higher_band="To reach 8.0, make examples more specific.",
        )


class _ErrorGrader:
    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        return Feedback(
            band=0.0,
            criteria={},
            summary="Automatic grading could not be completed: timeout",
            suggestions=["Try again."],
            error=True,
        )


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def retry_fixture(db):
    user = User(username="student", password="hashed")
    task = WritingTask(
        task_type=2,
        title="Task 2",
        prompt="Discuss both views.",
        min_words=5,
        duration_minutes=40,
    )
    db.add_all([user, task])
    db.flush()
    submission = WritingSubmission(
        user_id=user.id,
        task_id=task.id,
        text=(
            "Family influence matters because parents model behaviour every day. "
            "Schools can teach civic duties and teamwork, but children usually "
            "copy habits that they see repeatedly at home, so parental examples "
            "shape kindness, responsibility, and honesty. For this reason, a "
            "balanced approach is best, with teachers providing structure while "
            "families reinforce values through daily routines and conversations. "
            "This combination gives young people consistent guidance in different settings."
        ),
        word_count=54,
        status="failed",
        band=None,
        feedback={"band": 0.0, "criteria": {}, "summary": "old failure", "suggestions": []},
    )
    db.add(submission)
    db.flush()
    db.add(
        Mistake(
            user_id=user.id,
            submission_id=submission.id,
            skill="writing",
            category="vocabulary",
            subskill="old",
            severity=3,
        )
    )
    db.commit()
    return user, task, submission


async def _immediate_grading(grade, /, **kwargs):
    return grade(**kwargs)


def test_retry_updates_existing_failed_submission(monkeypatch, db, retry_fixture):
    user, _task, submission = retry_fixture
    submission_id = submission.id
    monkeypatch.setattr(writing, "get_writing_grader", lambda: _SuccessfulGrader())
    monkeypatch.setattr(writing, "run_grading", _immediate_grading)

    out = asyncio.run(
        writing.retry_submission(submission_id, db=db, current_user=user)
    )

    assert out["id"] == submission_id
    assert out["status"] == "graded"
    assert out["band"] == 7.5
    assert out["feedback"]["why_not_higher_band"] == (
        "To reach 8.0, make examples more specific."
    )

    rows = db.query(Mistake).filter(Mistake.submission_id == submission_id).all()
    assert len(rows) == 1
    assert rows[0].category == "grammar"
    assert rows[0].subskill == "articles"


def test_retry_keeps_submission_failed_when_grading_fails(monkeypatch, db, retry_fixture):
    user, _task, submission = retry_fixture
    monkeypatch.setattr(writing, "get_writing_grader", lambda: _ErrorGrader())
    monkeypatch.setattr(writing, "run_grading", _immediate_grading)

    out = asyncio.run(
        writing.retry_submission(submission.id, db=db, current_user=user)
    )

    assert out["id"] == submission.id
    assert out["status"] == "failed"
    assert out["band"] is None
    assert out["feedback"]["summary"].startswith("Automatic grading could not be completed")
    assert db.query(Mistake).filter(Mistake.submission_id == submission.id).count() == 0


def test_retry_rejects_non_failed_submission(monkeypatch, db, retry_fixture):
    user, _task, submission = retry_fixture
    submission.status = "graded"
    submission.band = 6.5
    db.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(writing.retry_submission(submission.id, db=db, current_user=user))

    assert exc.value.status_code == 409
