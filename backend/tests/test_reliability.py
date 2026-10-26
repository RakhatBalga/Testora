"""Global AI budget, stuck-grading reconciliation, pre-check refunds, idempotency."""
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application import attempts as attempts_service
from app.application import writing as writing_service
from app.application.quota import quota_status, reconcile_stale_reservations, reserve_ai_call
from app.application.writing import reconcile_stale_writing, submit_writing
from app.domain.models.ai_quota import AIGlobalBudget, AIQuotaBucket, AIReservation
from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.test import Question, Section, Test as ContentTest
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.domain.scoring import grade_attempt, build_breakdown, normalize_answer
from app.infrastructure.ai.base import Feedback
from app.infrastructure.config import settings
from app.infrastructure.database import Base
from app.infrastructure.time import utcnow

ESSAY = (
    "Family influence matters because parents model behaviour every day. Schools can teach civic duties "
    "and teamwork, but children usually copy habits that they see repeatedly at home, so parental examples "
    "shape kindness, responsibility, and honesty. For this reason, a balanced approach is best, with teachers "
    "providing structure while families reinforce values through daily routines and conversations. "
    "This combination gives young people consistent guidance in different settings."
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([User(id=1, username="a", password="x"), User(id=2, username="b", password="x"),
                         WritingTask(id=1, task_type=2, title="T", prompt="P", min_words=5, duration_minutes=40)])
        session.commit()
        yield session
    engine.dispose()


class _Grader:
    calls = 0

    def grade(self, **kwargs):
        type(self).calls += 1
        return Feedback(band=7.0, criteria={"Task Response": 7.0}, summary="ok")

    def improve(self, **kwargs):
        return None


# ---- global daily AI budget -------------------------------------------------

def test_global_budget_fails_closed_across_users(db, monkeypatch):
    monkeypatch.setattr(settings, "AI_GLOBAL_DAILY_ATTEMPTS", 2)
    for user_id in (1, 2):
        with reserve_ai_call(db, db.get(User, user_id), "vocabulary") as reservation:
            reservation.success = True
    with pytest.raises(HTTPException) as error:
        with reserve_ai_call(db, db.get(User, 1), "vocabulary"):
            pytest.fail("Provider must not be called once the global budget is spent")
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "ai_global_budget_exhausted"
    assert db.query(AIGlobalBudget).one().used == 2
    # The refused call did not charge the user's own daily budget either.
    assert db.query(AIQuotaBucket).filter_by(user_id=1, kind="attempts").one().used == 1


def test_global_budget_can_be_disabled(db, monkeypatch):
    monkeypatch.setattr(settings, "AI_GLOBAL_DAILY_ATTEMPTS", -1)
    with reserve_ai_call(db, db.get(User, 1), "vocabulary"):
        pass
    assert db.query(AIGlobalBudget).count() == 0


# ---- stuck pending submissions ----------------------------------------------

def _stuck_submission(db, minutes_old):
    sub = WritingSubmission(user_id=1, task_id=1, text=ESSAY, word_count=60, status="pending",
                            created_at=utcnow() - timedelta(minutes=minutes_old),
                            status_updated_at=utcnow() - timedelta(minutes=minutes_old))
    db.add(sub)
    db.commit()
    return sub


def test_stale_pending_is_failed_and_fresh_pending_is_left_alone(db):
    stale = _stuck_submission(db, settings.GRADING_STALE_MINUTES + 5)
    fresh = _stuck_submission(db, 1)
    assert reconcile_stale_writing(db) == 1
    db.refresh(stale)
    db.refresh(fresh)
    assert stale.status == "failed" and stale.band is None
    assert "not used" in stale.feedback["summary"]
    assert fresh.status == "pending"


def test_dead_worker_reservation_is_refunded_and_retry_unblocked(db, monkeypatch):
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 2)
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: _Grader())
    stale = _stuck_submission(db, settings.GRADING_STALE_MINUTES + 5)
    # The killed worker had reserved a review and held the retry lock.
    db.add(AIReservation(id="dead", user_id=1, kind="writing", charged=True, status="reserved",
                         active_resource=f"writing:{stale.id}",
                         created_at=utcnow() - timedelta(minutes=settings.GRADING_STALE_MINUTES + 5)))
    db.add(AIQuotaBucket(user_id=1, kind="writing", period="lifetime", used=1))
    db.commit()
    assert quota_status(db, WritingSubmission, db.get(User, 1), 2)["used"] == 0  # refunded lazily

    result = writing_service.retry_writing(db, db.get(User, 1), stale.id)  # no 409 forever

    assert result.status == "graded" and result.band == 7.0
    assert quota_status(db, WritingSubmission, db.get(User, 1), 2)["used"] == 1
    assert db.get(AIReservation, "dead").status == "expired"


def test_reservation_sweep_ignores_recent_reservations(db):
    db.add(AIReservation(id="live", user_id=1, kind="writing", charged=True, status="reserved"))
    db.commit()
    assert reconcile_stale_reservations(db) == 0


# ---- pre-check rejections are free ------------------------------------------

def test_precheck_rejection_costs_no_review_and_no_ai_call(db, monkeypatch):
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 1)
    _Grader.calls = 0
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: _Grader())
    user, task = db.get(User, 1), db.get(WritingTask, 1)

    rejected = submit_writing(db, user, task, "Too short.")

    assert rejected.status == "graded" and rejected.band == 0.0
    assert _Grader.calls == 0
    assert db.query(AIReservation).count() == 0
    assert quota_status(db, WritingSubmission, user, 1) == {"limit": 1, "used": 0, "remaining": 1, "exempt": False}
    real = submit_writing(db, user, task, ESSAY)  # the single free review is still available
    assert real.band == 7.0
    assert quota_status(db, WritingSubmission, user, 1)["remaining"] == 0


def test_rejection_still_answers_when_reviews_are_exhausted(db, monkeypatch):
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 0)
    out = submit_writing(db, db.get(User, 1), db.get(WritingTask, 1), "nope")
    assert out.band == 0.0


def test_identical_double_submit_returns_one_essay_and_one_charge(db, monkeypatch):
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 2)
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: _Grader())
    user, task = db.get(User, 1), db.get(WritingTask, 1)
    first = submit_writing(db, user, task, ESSAY)
    second = submit_writing(db, user, task, ESSAY)
    assert first.id == second.id
    assert quota_status(db, WritingSubmission, user, 2)["used"] == 1


def test_grader_error_text_never_reaches_the_user(db, monkeypatch):
    class Broken(_Grader):
        def grade(self, **kwargs):
            return Feedback(band=0.0, criteria={}, summary="403 PERMISSION_DENIED key=AIza...", error=True)

    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 2)
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: Broken())
    out = submit_writing(db, db.get(User, 1), db.get(WritingTask, 1), ESSAY)
    assert out.status == "failed"
    assert "PERMISSION_DENIED" not in str(out.feedback)
    assert quota_status(db, WritingSubmission, db.get(User, 1), 2)["used"] == 0


# ---- answers and attempts ---------------------------------------------------

@pytest.mark.parametrize("given, expected", [
    ("the  river", "the river"), ("River.", "river"), ("  “River” ", "river"),
    ("it’s", "it's"), ("A, ", "a"),
])
def test_answer_normalisation(given, expected):
    assert normalize_answer(given) == expected


@pytest.fixture()
def reading_db(db):
    test = ContentTest(id=1, title="R", test_type="reading", duration_minutes=60)
    section = Section(id=1, test_id=1, order=0, title="S")
    db.add_all([test, section,
                Question(id=1, section_id=1, order=1, text="q", question_type="fill_blank",
                         correct_answer=["the river"]),
                Question(id=2, section_id=1, order=2, text="q2", question_type="fill_blank",
                         correct_answer=["it's"])])
    db.commit()
    return db


def test_punctuation_and_spacing_do_not_fail_a_correct_answer(reading_db):
    questions = reading_db.query(Question).all()
    graded, score = grade_attempt(questions, {1: "The  river.", 2: "it’s"})
    assert score == 2 and build_breakdown(graded)[0]["accuracy"] == 100


def test_repeated_submission_key_returns_the_same_attempt(reading_db):
    user, test = reading_db.get(User, 1), reading_db.get(ContentTest, 1)
    graded = [{"question_id": 1, "user_answer": "x", "is_correct": False, "question_type": "fill_blank"}]
    kwargs = dict(graded=graded, score=0, total=1, breakdown=[], review_map={}, duration_seconds=10,
                  submission_key="key-12345678")
    first, created_first = attempts_service.save_graded_attempt(reading_db, user, test, **kwargs)
    second, created_second = attempts_service.save_graded_attempt(reading_db, user, test, **kwargs)
    assert created_first and not created_second and first.id == second.id
    assert reading_db.query(Attempt).count() == 1 and reading_db.query(AnswerRecord).count() == 1


def test_identical_submit_without_key_is_deduplicated_but_retake_is_not(reading_db):
    user, test = reading_db.get(User, 1), reading_db.get(ContentTest, 1)

    def graded(answer):
        return [{"question_id": 1, "user_answer": answer, "is_correct": False, "question_type": "fill_blank"}]

    base = dict(score=0, total=1, breakdown=[], review_map={}, duration_seconds=None)
    one, _ = attempts_service.save_graded_attempt(reading_db, user, test, graded=graded("x"), **base)
    again, created = attempts_service.save_graded_attempt(reading_db, user, test, graded=graded("x"), **base)
    other, created_other = attempts_service.save_graded_attempt(reading_db, user, test, graded=graded("y"), **base)
    assert again.id == one.id and not created
    assert created_other and other.id != one.id


# ---- grading gate (sync handlers must not hang or starve the threadpool) -----

def test_gate_rejects_excess_requests_with_503_instead_of_queueing(monkeypatch):
    import threading

    from app.application import ai_gate

    monkeypatch.setattr(ai_gate, "_admission", threading.BoundedSemaphore(1))
    with ai_gate.grading_admission():
        with pytest.raises(HTTPException) as error:
            with ai_gate.grading_admission():
                pytest.fail("second request must be refused while the first is in flight")
    assert error.value.status_code == 503 and error.value.headers["Retry-After"]
    with ai_gate.grading_admission():  # slot is released afterwards
        pass


def test_slot_wait_times_out_with_503(monkeypatch):
    import threading

    from app.application import ai_gate

    monkeypatch.setattr(ai_gate, "_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(settings, "GRADING_QUEUE_TIMEOUT_SECONDS", 0)
    ai_gate._slots.acquire()
    with pytest.raises(HTTPException) as error:
        ai_gate.run_graded(lambda: pytest.fail("must not run without a slot"))
    assert error.value.status_code == 503


def test_pair_runs_both_calls_and_tolerates_a_failing_secondary():
    from app.application import ai_gate

    def boom():
        raise RuntimeError("rewrite failed")

    primary, secondary = ai_gate.run_graded_pair(lambda: "graded", {}, boom, {})
    assert primary == "graded" and isinstance(secondary, RuntimeError)
