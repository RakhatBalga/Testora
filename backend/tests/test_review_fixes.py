"""Regressions for the backend review: rejected essays in learning, Reading evidence
before submission, orphaned gradings, resubmits, the daily quiz and write races."""

import asyncio
import logging
import secrets
from datetime import timedelta

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.api.routers import auth
from app.api.schemas.auth import GoogleAuthRequest, GoogleStartRequest
from app.api.schemas.listening import ListeningProgressIn
from app.application import google_auth, vocabulary
from app.application import writing as writing_service
from app.application.analytics.progress import compute_progress_impact
from app.application.learning import study_plan
from app.application.learning.dashboard import dashboard_summary
from app.application.learning.diagnostic import refresh_diagnostic, start_diagnostic
from app.application.learning.study_plan import get_weekly_plan
from app.application.listening import service as listening_service
from app.application.quota import quota_status
from app.application.writing import reconcile_stale_writing, submit_writing
from app.domain.models import speaking as _speaking_models, stored_file as _stored_file_model  # noqa: F401 (tables)
from app.domain.models.ai_quota import AIQuotaBucket, AIReservation
from app.domain.models.attempt import ListeningProgress
from app.domain.models.learning import StudyPlanItem
from app.domain.models.test import Question, Section, Test as ContentTest
from app.domain.models.user import User
from app.domain.models.vocabulary import DailyWordQuiz, SavedWord
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure import ratelimit
from app.infrastructure.ai.base import Feedback
from app.infrastructure.ai.vocab import MockVocabularyCoach
from app.infrastructure.config import settings
from app.infrastructure.database import Base
from app.infrastructure.time import local_today, utcnow

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
        session.add_all(
            [
                User(id=1, username="student", password="x"),
                WritingTask(id=1, task_type=2, title="T", prompt="P", min_words=5, duration_minutes=40),
            ]
        )
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture()
def two_sessions(tmp_path):
    """Two sessions on separate connections, to interleave a competing write."""
    engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    first, second = factory(), factory()
    try:
        yield first, second
    finally:
        first.close()
        second.close()
        engine.dispose()


def _compete_once(session, model, write):
    """Run `write(new_row)` just before `session` first flushes a new `model` row."""
    state = {"done": False}

    @event.listens_for(session, "before_flush")
    def _before_flush(sess, flush_context, instances):
        new = [obj for obj in sess.new if isinstance(obj, model)]
        if new and not state["done"]:
            state["done"] = True
            write(new[0])

    return state


class _Grader:
    def __init__(self):
        self.calls = 0

    def grade(self, **kwargs):
        self.calls += 1
        return Feedback(band=7.0, criteria={"Task Response": 7.0}, summary="ok")

    def improve(self, **kwargs):
        return None


def _submission(db, *, status="graded", band=None, minutes_old=0, feedback=None, text=ESSAY):
    at = utcnow() - timedelta(minutes=minutes_old)
    sub = WritingSubmission(
        user_id=1,
        task_id=1,
        text=text,
        word_count=60,
        status=status,
        band=band,
        feedback=feedback,
        created_at=at,
        status_updated_at=at,
    )
    db.add(sub)
    db.commit()
    return sub


# ---- 1. a rejected (Band 0) essay is not a graded attempt ---------------------


def test_rejected_essay_does_not_complete_the_diagnostic(db):
    start_diagnostic(db, 1, ["writing"])
    rejected = submit_writing(db, db.get(User, 1), db.get(WritingTask, 1), "asdf")
    assert rejected.status == "graded" and rejected.band == 0

    state = refresh_diagnostic(db, 1)
    assert state["status"] == "in_progress"
    assert state["provisional_level"] is None

    _submission(db, band=6.5, feedback={"criteria": {"Task Response": 6.5}})
    state = refresh_diagnostic(db, 1)
    assert state["status"] == "completed"
    assert state["provisional_level"] == 6.5


def test_rejected_essay_is_ignored_by_dashboard_plan_and_progress(db):
    graded = _submission(db, band=6.0, minutes_old=60, feedback={"criteria": {"Task Response": 6.0}})
    rejected = _submission(db, band=0.0, feedback={"criteria": {}})
    user = db.get(User, 1)

    summary = dashboard_summary(db, user)
    assert [row["id"] for row in summary["recent"]] == [f"writing-{graded.id}"]
    assert summary["profile"]["current_level"] == 6.0
    assert summary["weaknesses"]["writing"]["label"] == "Task Response"

    criterion, band, latest = study_plan._writing_signal(db, 1)
    assert (criterion, band, latest.id) == ("Task Response", 6.0, graded.id)
    # The plan was built after the graded essay; a later rejection is not a new result.
    plan_items = db.query(StudyPlanItem).all()
    assert plan_items and study_plan._has_new_results(db, 1, plan_items) is False

    assert compute_progress_impact(db, 1, "writing", rejected.id)["found"] is False
    assert compute_progress_impact(db, 1, "writing", graded.id)["found"] is True


# ---- 2. Reading evidence is not sent before the first submission -------------


def test_reading_evidence_is_hidden_until_the_test_is_submitted(api):
    with api.Session() as db:
        test = ContentTest(title="R", test_type="reading", duration_minutes=60, content_metadata={"published": True})
        section = Section(order=1, title="Passage 1", passage="Solar power is widely available.")
        section.questions = [
            Question(
                order=1,
                text="What is widely available?",
                question_type="short_answer",
                correct_answer=["solar power"],
                evidence=[{"paragraph": 1, "text": "Solar power is widely available."}],
            )
        ]
        test.sections = [section]
        db.add(test)
        db.commit()
        test_id, question_id = test.id, section.questions[0].id
    spans = [{"paragraph": 1, "text": "Solar power is widely available."}]

    before = api.client.get(f"/tests/{test_id}", headers=api.headers).json()
    question = before["sections"][0]["questions"][0]
    assert question["evidence"] is None
    assert question["text"] == "What is widely available?" and before["sections"][0]["passage"]
    assert "Solar power is widely available." not in str(before["sections"][0]["questions"])

    submitted = api.client.post(
        "/results/submit",
        headers=api.headers,
        json={"test_id": test_id, "answers": [{"question_id": question_id, "answer": "wind"}]},
    ).json()
    assert submitted["answers"][0]["evidence"] == spans

    stored = api.client.get(f"/results/{submitted['id']}", headers=api.headers).json()
    assert stored["answers"][0]["evidence"] == spans
    # Clients that read evidence from the test payload get it once an attempt exists.
    after = api.client.get(f"/tests/{test_id}", headers=api.headers).json()
    assert after["sections"][0]["questions"][0]["evidence"] == spans


# ---- 3. gradings orphaned by the previous process ----------------------------


def test_orphan_sweep_fails_gradings_started_before_boot_and_refunds_them(db, monkeypatch):
    orphan = _submission(db, status="pending", minutes_old=1)  # far inside the stale window
    db.add(
        AIReservation(
            id="dead",
            user_id=1,
            kind="writing",
            charged=True,
            status="reserved",
            active_resource=f"writing:{orphan.id}",
        )
    )
    db.add(AIQuotaBucket(user_id=1, kind="writing", period="lifetime", used=1))
    db.commit()
    booted_at = utcnow()
    live = _submission(db, status="pending", text=ESSAY + " More.")  # started by this process
    live.status_updated_at = booted_at + timedelta(seconds=5)
    db.commit()

    # The lazy per-user sweep still waits for the stale window.
    assert reconcile_stale_writing(db, 1) == 0
    assert orphan.status == "pending"

    monkeypatch.setattr(main, "SessionLocal", lambda: Session(db.get_bind()))
    assert main._reconcile_orphaned_gradings(booted_at) == 1

    db.expire_all()
    assert orphan.status == "failed" and orphan.band is None
    assert "not used" in orphan.feedback["summary"]
    assert live.status == "pending"
    assert db.get(AIReservation, "dead").status == "expired"
    assert db.query(AIQuotaBucket).filter_by(kind="writing").one().used == 0
    # No longer stuck: the orphan can be retried straight away.
    monkeypatch.setattr(writing_service, "get_writing_grader", _Grader)
    assert writing_service.retry_writing(db, db.get(User, 1), orphan.id).status == "graded"


def test_orphan_sweep_waits_for_the_previous_process_to_stop(monkeypatch):
    order = []

    async def fake_sleep(seconds):
        order.append(("sleep", seconds))

    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(main, "_reconcile_orphaned_gradings", lambda booted_at: order.append(("sweep", booted_at)))
    booted_at = utcnow()

    asyncio.run(main._sweep_orphans_after_handover(booted_at))

    assert order == [("sleep", main.ORPHAN_SWEEP_DELAY_SECONDS), ("sweep", booted_at)]


# ---- 4. resubmitting the same essay ------------------------------------------


def test_resubmit_while_the_first_request_is_grading_returns_the_pending_submission(db, monkeypatch):
    grader = _Grader()
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: grader)
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 1)
    # The first request is still in flight after eight minutes (the browser gave up at seven).
    pending = _submission(db, status="pending", minutes_old=8)
    db.add(AIQuotaBucket(user_id=1, kind="writing", period="lifetime", used=1))  # it holds the last review
    db.commit()

    again = submit_writing(db, db.get(User, 1), db.get(WritingTask, 1), ESSAY)

    assert again.id == pending.id and again.status == "pending"
    assert db.query(WritingSubmission).count() == 1
    assert grader.calls == 0


def test_resubmit_after_grading_returns_the_same_review_without_a_second_charge(db, monkeypatch):
    grader = _Grader()
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: grader)
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 1)
    user, task = db.get(User, 1), db.get(WritingTask, 1)

    first = submit_writing(db, user, task, ESSAY)
    assert first.status == "graded" and first.band == 7.0
    # Slow grading: created nine minutes ago, finished one minute ago.
    first.created_at = utcnow() - timedelta(minutes=9)
    first.status_updated_at = utcnow() - timedelta(minutes=1)
    db.commit()

    again = submit_writing(db, user, task, ESSAY)  # the last free review is used: still not a 403

    assert again.id == first.id and again.status == "graded"
    assert db.query(WritingSubmission).count() == 1
    assert grader.calls == 1
    assert quota_status(db, WritingSubmission, user, 1)["used"] == 1


def test_same_text_is_a_new_submission_after_the_window_or_a_failure(db, monkeypatch):
    grader = _Grader()
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: grader)
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 5)
    user, task = db.get(User, 1), db.get(WritingTask, 1)
    old = _submission(db, band=6.0, minutes_old=11)
    failed = _submission(db, status="failed")

    fresh = submit_writing(db, user, task, ESSAY)

    assert fresh.id not in (old.id, failed.id) and fresh.status == "graded"
    assert grader.calls == 1


# ---- 5. daily quiz -----------------------------------------------------------


class _CountingCoach(MockVocabularyCoach):
    quizzes = 0

    def generate_quiz(self, **kwargs):
        type(self).quizzes += 1
        return super().generate_quiz(**kwargs)


def test_daily_quiz_without_saved_words_does_not_call_the_ai(db, monkeypatch):
    monkeypatch.setattr(_CountingCoach, "quizzes", 0)
    monkeypatch.setattr(vocabulary, "get_vocabulary_coach", _CountingCoach)
    user = db.get(User, 1)

    quiz = vocabulary.public_quiz(vocabulary.get_daily_quiz(db, user=user, quiz_date=local_today()))

    assert quiz["questions"] == [] and quiz["total"] == 0 and quiz["completed"] is False
    assert _CountingCoach.quizzes == 0
    assert db.query(AIReservation).count() == 0 and db.query(AIQuotaBucket).count() == 0
    assert db.query(DailyWordQuiz).count() == 0

    # Not cached: a word saved later the same day still gets a real quiz.
    db.add(SavedWord(user_id=1, word="alpha", context="The alpha value is high."))
    db.commit()
    vocabulary.get_daily_quiz(db, user=user, quiz_date=local_today())
    assert _CountingCoach.quizzes == 1 and db.query(DailyWordQuiz).count() == 1


def test_daily_quiz_is_graded_once(db):
    today = local_today()
    db.add(SavedWord(id=1, user_id=1, word="alpha", status="new"))
    db.add(
        DailyWordQuiz(
            user_id=1,
            quiz_date=today,
            total=1,
            payload={"questions": [{"word": "alpha", "prompt": "?", "options": ["a", "b"], "answer_index": 1}]},
        )
    )
    db.commit()

    first = vocabulary.grade_daily_quiz(db, user_id=1, quiz_date=today, answers=[1])
    assert first["score"] == 1
    assert db.get(SavedWord, 1).status == "learning"

    repeat = vocabulary.grade_daily_quiz(db, user_id=1, quiz_date=today, answers=[1])
    changed = vocabulary.grade_daily_quiz(db, user_id=1, quiz_date=today, answers=[0])

    assert repeat == first and changed == first  # the first grading stands
    assert db.get(SavedWord, 1).status == "learning"  # not advanced to "mastered" by repeats
    quiz = db.query(DailyWordQuiz).one()
    assert quiz.completed is True and quiz.score == 1
    assert "answers" not in str(vocabulary.public_quiz(quiz)["questions"])


# ---- 6. unique-constraint races ----------------------------------------------


def test_weekly_plan_survives_a_parallel_request_creating_it(two_sessions):
    db, other = two_sessions
    db.add(User(id=1, username="planner", password="x", weekly_study_days=3))
    db.add(WritingTask(id=1, task_type=2, title="T", prompt="P", min_words=250, duration_minutes=40))
    db.commit()

    def parallel_request(item):
        other.add(
            StudyPlanItem(
                user_id=1,
                week_start=item.week_start,
                stable_key=item.stable_key,
                title="Stored by the other request",
                reason=item.reason,
                minutes=item.minutes,
                skill=item.skill,
                action_type=item.action_type,
                href=item.href,
                scheduled_date=item.week_start,
                source_type=item.source_type,
            )
        )
        other.commit()

    raced = _compete_once(db, StudyPlanItem, parallel_request)

    plan = get_weekly_plan(db, db.get(User, 1))

    assert raced["done"]
    assert [item["title"] for item in plan["items"]] == ["Stored by the other request"]
    assert db.query(StudyPlanItem).count() == 1
    assert get_weekly_plan(db, db.get(User, 1))["total"] == 1


def test_listening_autosave_survives_a_parallel_first_save(two_sessions):
    db, other = two_sessions
    db.add(User(id=1, username="listener", password="x"))
    db.add(
        ContentTest(
            id=1,
            title="L",
            test_type="listening",
            duration_minutes=30,
            content_version="1.0.0",
            content_metadata={"published": True},
        )
    )
    db.commit()

    def parallel_autosave(row):
        other.add(ListeningProgress(user_id=1, test_id=1, content_version="1.0.0", mode="practice", answers={}))
        other.commit()

    raced = _compete_once(db, ListeningProgress, parallel_autosave)
    payload = ListeningProgressIn(
        content_version="1.0.0",
        mode="practice",
        answers={"1": "King"},
        current_section=0,
        audio_position=12.5,
        max_audio_position=12.5,
    )

    saved = listening_service.save_progress(db, db.get(User, 1), 1, payload)

    assert raced["done"]
    assert db.query(ListeningProgress).count() == 1
    assert saved.answers == {"1": "King"} and saved.audio_position == 12.5


def _google_sign_in(db, monkeypatch, *, google_id="google-user", email="student@example.com"):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setattr(settings, "CORS_ORIGINS", "http://localhost:3000")
    redirect = "http://localhost:3000/auth/google/callback"

    def handler(request):
        if request.url == google_auth.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "google-token"})
        return httpx.Response(200, json={"id": google_id, "email": email, "verified_email": True})

    client_type = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: client_type(transport=httpx.MockTransport(handler)))
    state = secrets.token_urlsafe(32)
    auth.google_start(GoogleStartRequest(state=state, redirect_uri=redirect), db)
    return auth.google_auth_endpoint(GoogleAuthRequest(code="code", state=state, redirect_uri=redirect), db)


def test_google_sign_up_retries_when_the_username_is_taken_in_parallel(two_sessions, monkeypatch):
    db, other = two_sessions

    def parallel_sign_up(user):
        other.add(User(username=user.username, password="x", email="someone-else@example.com"))
        other.commit()

    raced = _compete_once(db, User, parallel_sign_up)

    result = _google_sign_in(db, monkeypatch)

    assert raced["done"]
    assert result["username"] == "student1" and result["is_new_user"] is True
    assert db.query(User).count() == 2


def test_google_sign_up_uses_the_account_a_parallel_callback_created(two_sessions, monkeypatch):
    db, other = two_sessions

    def parallel_callback(user):
        other.add(User(username="winner", password="x", email=user.email, google_id=user.google_id))
        other.commit()

    _compete_once(db, User, parallel_callback)

    result = _google_sign_in(db, monkeypatch)

    assert result["username"] == "winner" and result["is_new_user"] is False
    assert db.query(User).count() == 1


# ---- 8. rate-limit diagnostics -----------------------------------------------


def test_rate_limited_request_logs_the_peer_and_forwarded_chain(caplog):
    from starlette.requests import Request

    def request():
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.20.0.7")],
            "client": ("10.20.0.1", 1234),
        }
        return Request(scope)

    limiter = ratelimit.RateLimiter(max_requests=1, window_seconds=60)
    asyncio.run(limiter(request()))
    with caplog.at_level(logging.INFO, logger="testora.ratelimit"), pytest.raises(HTTPException) as error:
        asyncio.run(limiter(request()))

    assert error.value.status_code == 429
    line = next(record.getMessage() for record in caplog.records if record.getMessage().startswith("Rate limited"))
    assert "bucket_ip=10.20.0.1" in line and "peer=10.20.0.1" in line
    assert "203.0.113.9, 10.20.0.7" in line
