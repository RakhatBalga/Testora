from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.learning.diagnostic import (
    accept_diagnostic_level,
    refresh_diagnostic,
    start_diagnostic,
)
from app.application.learning.notebook import list_notebook, set_mistake_status
from app.application.learning.study_plan import get_weekly_plan, set_plan_status
from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.mistake import Mistake
from app.domain.models.learning import StudyPlanItem
from app.domain.models.test import Question, Section, Test as ContentTest
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure.database import Base


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _content(db):
    writing_task = WritingTask(
        task_type=2,
        title="Discuss both views",
        prompt="Discuss both views and give your opinion.",
        min_words=250,
        duration_minutes=40,
    )
    reading_test = ContentTest(title="Reading A", test_type="reading", duration_minutes=60)
    section = Section(order=1, title="Passage 1", passage="Solar power is widely available.")
    question = Question(
        order=1,
        text="What is widely available?",
        question_type="short_answer",
        correct_answer=["solar power"],
        explanation="The first sentence states the answer.",
        evidence=[{"paragraph": 1, "text": "Solar power is widely available."}],
    )
    section.questions = [question]
    reading_test.sections = [section]
    db.add_all([writing_task, reading_test])
    db.flush()
    return writing_task, reading_test, question


def test_weekly_plan_is_idempotent_and_preserves_completed_items():
    db = _session()
    try:
        user = User(
            username="planner",
            password="hashed",
            weekly_study_days=3,
            daily_study_minutes=30,
            primary_focus="writing",
        )
        db.add(user)
        writing_task, reading_test, _ = _content(db)
        db.flush()
        writing = WritingSubmission(
            user_id=user.id,
            task_id=writing_task.id,
            text="A specific example supports this argument.",
            word_count=250,
            status="graded",
            band=6.5,
            feedback={"criteria": {"Task Response": 6.0, "Lexical Resource": 7.0}},
        )
        reading = Attempt(
            user_id=user.id,
            test_id=reading_test.id,
            score=1,
            total=2,
            band=5.5,
            breakdown=[{
                "question_type": "short_answer",
                "label": "Short Answer",
                "correct": 0,
                "total": 1,
                "accuracy": 0,
            }],
        )
        db.add_all([writing, reading])
        db.commit()

        first = get_weekly_plan(db, user)
        second = get_weekly_plan(db, user)

        assert [item["id"] for item in first["items"]] == [item["id"] for item in second["items"]]
        assert len({item["stable_id"] for item in first["items"]}) == len(first["items"])
        assert {item["skill"] for item in first["items"]} <= {"writing", "reading"}
        assert all(item["minutes"] <= user.daily_study_minutes for item in first["items"])
        assert all(item["href"] in {f"/writing/{writing_task.id}", f"/reading/{reading_test.id}"} for item in first["items"])

        completed_id = first["items"][0]["id"]
        set_plan_status(db, user.id, completed_id, "completed")
        recalculated = get_weekly_plan(db, user, recalculate=True)

        completed = next(item for item in recalculated["items"] if item["id"] == completed_id)
        assert completed["status"] == "completed"
    finally:
        db.close()


def test_weekly_plan_refreshes_when_a_new_reading_result_arrives():
    db = _session()
    try:
        user = User(username="adaptive", password="hashed", weekly_study_days=2)
        db.add(user)
        _, reading_test, _ = _content(db)
        db.commit()
        starter = get_weekly_plan(db, user)
        plan_time = max(item.updated_at for item in db.query(StudyPlanItem).all())
        db.add(Attempt(
            user_id=user.id,
            test_id=reading_test.id,
            score=10,
            total=40,
            band=4.5,
            breakdown=[{
                "question_type": "matching_headings",
                "label": "Matching Headings",
                "correct": 1,
                "total": 5,
                "accuracy": 20,
            }],
            created_at=plan_time + timedelta(seconds=1),
        ))
        db.commit()

        refreshed = get_weekly_plan(db, user)

        assert any(item["stable_id"] == "reading-type-matching-headings" for item in refreshed["items"])
        assert [item["stable_id"] for item in refreshed["items"]] != [item["stable_id"] for item in starter["items"]]
    finally:
        db.close()


def test_notebook_uses_exact_writing_quotes_and_enforces_reading_ownership():
    db = _session()
    try:
        user = User(username="owner", password="hashed")
        other = User(username="other", password="hashed")
        db.add_all([user, other])
        task, reading_test, question = _content(db)
        db.flush()
        submission = WritingSubmission(
            user_id=user.id,
            task_id=task.id,
            text="A specific example supports this argument.",
            word_count=250,
            status="graded",
            band=6.5,
            feedback={},
        )
        db.add(submission)
        db.flush()
        valid = Mistake(
            user_id=user.id,
            submission_id=submission.id,
            skill="writing",
            category="vocabulary",
            subskill="precision",
            severity=1,
            snippet="specific example",
            correction="a concrete example",
        )
        invented = Mistake(
            user_id=user.id,
            submission_id=submission.id,
            skill="writing",
            category="grammar",
            severity=1,
            snippet="phrase that was never written",
        )
        attempt = Attempt(user_id=user.id, test_id=reading_test.id, score=0, total=1, band=4.0)
        db.add_all([valid, invented, attempt])
        db.flush()
        record = AnswerRecord(
            attempt_id=attempt.id,
            question_id=question.id,
            user_answer="wind power",
            is_correct=False,
        )
        db.add(record)
        db.commit()

        notebook = list_notebook(db, user.id, page_size=20)
        writing_items = {item["source_id"]: item for item in notebook["items"] if item["skill"] == "writing"}
        reading_item = next(item for item in notebook["items"] if item["skill"] == "reading")

        assert writing_items[valid.id]["quote"] == "specific example"
        assert writing_items[invented.id]["quote"] is None
        assert reading_item["user_answer"] == "wind power"
        assert reading_item["correct_answer"] == "solar power"
        assert reading_item["evidence"][0]["paragraph"] == 1
        assert set_mistake_status(db, user.id, "reading", record.id, "mastered") is True
        assert set_mistake_status(db, other.id, "reading", record.id, "mastered") is False
    finally:
        db.close()


def test_diagnostic_requires_confirmation_before_updating_current_level():
    db = _session()
    try:
        user = User(username="diagnostic", password="hashed", current_level=None)
        db.add(user)
        task, reading_test, _ = _content(db)
        db.commit()
        state = start_diagnostic(db, user.id, ["writing", "reading"])
        started_at = state["started_at"]
        writing = WritingSubmission(
            user_id=user.id,
            task_id=task.id,
            text="Essay",
            word_count=250,
            status="graded",
            band=7.0,
            feedback={},
            created_at=started_at + timedelta(seconds=1),
        )
        reading = Attempt(
            user_id=user.id,
            test_id=reading_test.id,
            score=30,
            total=40,
            band=6.0,
            created_at=started_at + timedelta(seconds=1),
        )
        db.add_all([writing, reading])
        db.commit()

        completed = refresh_diagnostic(db, user.id)

        assert completed["status"] == "completed"
        assert completed["provisional_level"] == 6.5
        assert user.current_level is None

        accepted = accept_diagnostic_level(db, user)

        assert accepted["provisional_level"] == 6.5
        assert user.current_level == 6.5
        assert user.current_level_source == "diagnostic"
    finally:
        db.close()


def test_diagnostic_clamps_provisional_level_to_profile_range():
    db = _session()
    try:
        user = User(username="low-band", password="hashed")
        db.add(user)
        _, reading_test, _ = _content(db)
        db.commit()
        state = start_diagnostic(db, user.id, ["reading"])
        db.add(Attempt(
            user_id=user.id,
            test_id=reading_test.id,
            score=1,
            total=40,
            band=1.0,
            created_at=state["started_at"] + timedelta(seconds=1),
        ))
        db.commit()

        completed = refresh_diagnostic(db, user.id)

        assert completed["provisional_level"] == 4.0
    finally:
        db.close()


def test_accepting_higher_diagnostic_level_keeps_target_valid():
    db = _session()
    try:
        user = User(username="high-band", password="hashed", target_band=7.0)
        db.add(user)
        _, reading_test, _ = _content(db)
        db.commit()
        state = start_diagnostic(db, user.id, ["reading"])
        db.add(Attempt(
            user_id=user.id,
            test_id=reading_test.id,
            score=38,
            total=40,
            band=8.5,
            created_at=state["started_at"] + timedelta(seconds=1),
        ))
        db.commit()
        refresh_diagnostic(db, user.id)

        accept_diagnostic_level(db, user)

        assert user.current_level == 8.5
        assert user.target_band == 8.5
    finally:
        db.close()
