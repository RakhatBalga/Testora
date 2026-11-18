"""Writing idempotency key, SQL-bounded history/notebook pages, Reading/Listening
weaknesses and tolerant settings. The database tests run on SQLite and, when
TEST_POSTGRES_URL is set (CI), on PostgreSQL."""

import os
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from app.application import writing as writing_service
from app.application.analytics.weakness import compute_recurring_mistakes, compute_weaknesses
from app.application.history import history_page
from app.application.learning.notebook import list_notebook, notebook_summary
from app.application.quota import quota_status
from app.application.writing import submit_writing
from app.domain.models import speaking as _speaking_models, stored_file as _stored_file_model  # noqa: F401 (tables)
from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.learning import MistakeReview
from app.domain.models.mistake import Mistake
from app.domain.models.speaking import SpeakingSubmission, SpeakingTask
from app.domain.models.test import Question, Section, Test as ContentTest
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure.ai.base import Feedback
from app.infrastructure.config import Settings, settings
from app.infrastructure.database import Base
from app.infrastructure.time import utcnow

ESSAY = (
    "Family influence matters because parents model behaviour every day. Schools can teach civic duties "
    "and teamwork, but children usually copy habits that they see repeatedly at home, so parental examples "
    "shape kindness, responsibility, and honesty. For this reason, a balanced approach is best, with teachers "
    "providing structure while families reinforce values through daily routines and conversations. "
    "This combination gives young people consistent guidance in different settings."
)
T0 = datetime(2026, 1, 1, 12, 0, 0)


@pytest.fixture(params=["sqlite", "postgresql"])
def db(request, tmp_path):
    admin = None
    if request.param == "postgresql":
        url = os.environ.get("TEST_POSTGRES_URL")
        if not url:
            pytest.skip("TEST_POSTGRES_URL required; enabled in CI")
        schema = "test_" + uuid.uuid4().hex
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(f"sqlite:///{tmp_path / 'round2.db'}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            session.add(User(id=1, username="student", password="x"))
            session.add(WritingTask(task_type=2, title="Essay", prompt="P", min_words=5, duration_minutes=40))
            session.commit()
            yield session
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


class _Grader:
    def __init__(self, error=False):
        self.calls = 0
        self.error = error

    def grade(self, **kwargs):
        self.calls += 1
        if self.error:
            return Feedback(band=0.0, criteria={}, summary="provider timeout", error=True)
        return Feedback(band=7.0, criteria={"Task Response": 7.0}, summary="ok")

    def improve(self, **kwargs):
        return None


def _loads(model):
    """Count ORM rows of `model` fetched from the database from now on."""
    counter = {"rows": 0}

    def _on_load(target, context):
        counter["rows"] += 1

    event.listen(model, "load", _on_load)
    counter["stop"] = lambda: event.remove(model, "load", _on_load)
    return counter


# ---- 1. Writing submission_key -------------------------------------------------


def test_same_submission_key_returns_the_first_submission_without_a_second_charge(db, monkeypatch):
    grader = _Grader()
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: grader)
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 1)
    user, task = db.get(User, 1), db.query(WritingTask).one()

    first = submit_writing(db, user, task, ESSAY, submission_key="key-00000001")
    assert first.status == "graded" and first.submission_key == "key-00000001"
    # Long after the text-based window, and with the last free review used.
    first.created_at = first.status_updated_at = utcnow() - timedelta(hours=3)
    db.commit()

    again = submit_writing(db, user, task, ESSAY, submission_key="key-00000001")
    edited = submit_writing(db, user, task, ESSAY + " Edited.", submission_key="key-00000001")

    assert again.id == first.id and edited.id == first.id
    assert db.query(WritingSubmission).count() == 1
    assert grader.calls == 1
    assert quota_status(db, WritingSubmission, user, 1)["used"] == 1


@pytest.mark.parametrize("status", ["pending", "failed"])
def test_submission_key_returns_the_original_whatever_its_status(db, monkeypatch, status):
    grader = _Grader()
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: grader)
    user, task = db.get(User, 1), db.query(WritingTask).one()
    original = WritingSubmission(
        user_id=1,
        task_id=task.id,
        text=ESSAY,
        word_count=60,
        status=status,
        status_updated_at=utcnow(),
        submission_key="key-00000002",
    )
    db.add(original)
    db.commit()

    again = submit_writing(db, user, task, ESSAY, submission_key="key-00000002")

    assert again.id == original.id and again.status == status
    assert grader.calls == 0 and db.query(WritingSubmission).count() == 1


def test_submission_key_covers_rejected_and_failed_first_requests(db, monkeypatch):
    grader = _Grader(error=True)
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: grader)
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 2)
    user, task = db.get(User, 1), db.query(WritingTask).one()

    rejected = submit_writing(db, user, task, "asdf", submission_key="key-rejected")
    assert (
        rejected.band == 0 and submit_writing(db, user, task, "asdf", submission_key="key-rejected").id == rejected.id
    )

    failed = submit_writing(db, user, task, ESSAY, submission_key="key-failed-1")
    assert failed.status == "failed"
    assert submit_writing(db, user, task, ESSAY, submission_key="key-failed-1").id == failed.id
    assert grader.calls == 1
    # The retry endpoint still regrades the same row and keeps its key.
    grader.error = False
    retried = writing_service.retry_writing(db, user, failed.id)
    assert retried.id == failed.id and retried.status == "graded" and retried.submission_key == "key-failed-1"
    assert db.query(WritingSubmission).count() == 2
    assert quota_status(db, WritingSubmission, user, 2)["used"] == 1


def test_a_new_key_is_a_new_submission_and_no_key_falls_back_to_text(db, monkeypatch):
    grader = _Grader()
    monkeypatch.setattr(writing_service, "get_writing_grader", lambda: grader)
    monkeypatch.setattr(settings, "FREE_WRITING_SUBMISSIONS", 5)
    user, task = db.get(User, 1), db.query(WritingTask).one()

    first = submit_writing(db, user, task, ESSAY, submission_key="key-00000003")
    by_text = submit_writing(db, user, task, ESSAY)  # old client, no key: matched by text
    new_key = submit_writing(db, user, task, ESSAY, submission_key="key-00000004")

    assert by_text.id == first.id
    assert new_key.id != first.id and new_key.submission_key == "key-00000004"
    assert grader.calls == 2


def test_writing_submit_validates_the_key_like_reading(api):
    with api.Session() as session:
        session.add(WritingTask(id=1, task_type=2, title="Essay", prompt="P", min_words=5, duration_minutes=40))
        session.commit()
    for bad in ("short", "has space in it", "x" * 81):
        response = api.client.post(
            "/writing/submit", headers=api.headers, json={"task_id": 1, "text": "asdf", "submission_key": bad}
        )
        assert response.status_code == 422, bad

    body = {"task_id": 1, "text": "asdf", "submission_key": "0b9f6c1e-1c1d-4b61-9a53-7d1f5a2f8a10"}
    first = api.client.post("/writing/submit", headers=api.headers, json=body)
    second = api.client.post("/writing/submit", headers=api.headers, json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert (
        api.client.post("/writing/submit", headers=api.headers, json={"task_id": 1, "text": "asdf"}).status_code == 200
    )


# ---- 2. history and notebook pages are bounded in SQL --------------------------


def _reading_test(db, test_type="reading", types=("matching", "true_false", "short_answer")):
    test = ContentTest(title=f"{test_type} test", test_type=test_type, content_metadata={"published": True})
    section = Section(order=1, title="Part 1", passage="Solar power is widely available.")
    section.questions = [
        Question(
            order=index + 1,
            text=f"Q{index + 1}",
            question_type=types[index % len(types)],
            correct_answer=["a"],
            evidence=[{"paragraph": 1, "text": "Solar power is widely available."}],
            question_metadata={"target_skill": ("detail", "gist")[index % 2]} if test_type == "listening" else None,
        )
        for index in range(12)
    ]
    test.sections = [section]
    db.add(test)
    db.flush()
    return test


def _attempt(db, test, created_at, wrong, band=6.0):
    """One attempt answering every question; `wrong` = indexes answered incorrectly."""
    questions = test.sections[0].questions
    attempt = Attempt(user_id=1, test_id=test.id, score=len(questions) - len(wrong), total=len(questions), band=band)
    attempt.created_at = created_at
    attempt.answers = [
        AnswerRecord(question_id=question.id, user_answer="b" if index in wrong else "a", is_correct=index not in wrong)
        for index, question in enumerate(questions)
    ]
    db.add(attempt)
    db.flush()
    return attempt


def _history_reference(db, skill, sort):
    """The previous implementation: load everything, sort and slice in Python."""
    from app.application.history.history import _item
    from app.application import frontend_routes as routes

    items = []
    newest = lambda model: (model.created_at.desc(), model.id.desc())  # noqa: E731
    if not skill or skill == "writing":
        for r in db.query(WritingSubmission).order_by(*newest(WritingSubmission)).all():
            items.append(
                _item(
                    "writing",
                    r.id,
                    r.task.title,
                    r.band,
                    None,
                    None,
                    r.status,
                    r.created_at,
                    routes.result("writing", r.id),
                )
            )
    if not skill or skill == "speaking":
        for r in db.query(SpeakingSubmission).order_by(*newest(SpeakingSubmission)).all():
            status = "graded" if r.band is not None else "pending"
            items.append(
                _item(
                    "speaking",
                    r.id,
                    f"Speaking Part {r.task.part}",
                    r.band,
                    None,
                    None,
                    status,
                    r.created_at,
                    routes.result("speaking", r.id),
                )
            )
    for name in ("reading", "listening"):
        if skill and skill != name:
            continue
        rows = (
            db.query(Attempt).join(ContentTest).filter(ContentTest.test_type == name).order_by(*newest(Attempt)).all()
        )
        for r in rows:
            items.append(
                _item(
                    name,
                    r.id,
                    r.test.title,
                    r.band,
                    r.score,
                    r.total,
                    "graded",
                    r.created_at,
                    routes.result(name, r.id),
                )
            )
    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    if sort == "oldest":
        items.sort(key=lambda x: x["created_at"] or "")
    elif sort == "highest":
        items.sort(key=lambda x: (x["band"] is None, -(x["band"] or 0)))
    elif sort == "lowest":
        items.sort(key=lambda x: (x["band"] is None, x["band"] or 0))
    return items


def _seed_history(db):
    task = db.query(WritingTask).one()
    speaking_task = SpeakingTask(part=2, questions=["Describe a place."])
    db.add(speaking_task)
    reading, listening = _reading_test(db), _reading_test(db, "listening")
    bands = [None, 5.0, 5.5, 6.0, 6.5, 7.0, 6.0, 5.5]
    for index in range(40):
        # Timestamps repeat across and inside sources, so ties are exercised too.
        at = T0 + timedelta(minutes=(index * 7) % 23)
        band = bands[index % len(bands)]
        db.add(
            WritingSubmission(
                user_id=1,
                task_id=task.id,
                text="t",
                word_count=1,
                status="graded" if band else "failed",
                band=band,
                created_at=at,
            )
        )
        db.add(SpeakingSubmission(user_id=1, task_id=speaking_task.id, audio_url="a", band=band, created_at=at))
        _attempt(db, reading, at, wrong=set(), band=bands[(index + 3) % len(bands)])
        _attempt(db, listening, at + timedelta(minutes=1), wrong=set(), band=bands[(index + 5) % len(bands)])
    db.commit()


@pytest.mark.parametrize("skill", [None, "writing", "speaking", "reading", "listening"])
@pytest.mark.parametrize("sort", ["newest", "oldest", "highest", "lowest"])
def test_history_pages_match_the_unbounded_result(db, skill, sort):
    _seed_history(db)
    expected = _history_reference(db, skill, sort)
    assert len(expected) == (40 if skill else 160)

    for page, page_size in ((1, 10), (2, 10), (3, 7), (4, 50), (17, 10), (1, 50)):
        result = history_page(db, 1, skill, sort, page, page_size)
        start = (page - 1) * page_size
        assert result["total"] == len(expected)
        assert result["items"] == expected[start : start + page_size], (page, page_size)


def test_history_page_reads_only_the_rows_a_page_can_need(db):
    _seed_history(db)
    db.expire_all()
    attempts, essays = _loads(Attempt), _loads(WritingSubmission)
    try:
        result = history_page(db, 1, None, "newest", 2, 10)
    finally:
        attempts["stop"](), essays["stop"]()

    assert len(result["items"]) == 10 and result["total"] == 160
    # 80 attempts and 40 essays exist; page 2 of 10 needs at most 20 per source.
    assert attempts["rows"] <= 40 and essays["rows"] <= 20


def _notebook_reference(db, skill, status):
    """The previous implementation: every item of every source, filtered in Python."""
    statuses = {(r.skill, r.source_id): r.status for r in db.query(MistakeReview).all()}
    items = []
    if skill in (None, "writing"):
        for mistake in db.query(Mistake).filter(Mistake.skill == "writing").all():
            items.append(("writing", mistake.id, mistake.created_at))
    for name in ("reading", "listening"):
        if skill not in (None, name):
            continue
        rows = (
            db.query(AnswerRecord, Attempt)
            .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
            .join(ContentTest, Attempt.test_id == ContentTest.id)
            .filter(ContentTest.test_type == name, AnswerRecord.is_correct.is_(False))
            .all()
        )
        items.extend((name, record.id, attempt.created_at) for record, attempt in rows)
    items = [
        {"id": f"{name}-{source_id}", "status": statuses.get((name, source_id), "new"), "created_at": created_at}
        for name, source_id, created_at in items
    ]
    if status:
        items = [item for item in items if item["status"] == status]
    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return items


def _seed_notebook(db):
    task = db.query(WritingTask).one()
    essay = WritingSubmission(user_id=1, task_id=task.id, text="An essay.", word_count=2, status="graded", band=6.0)
    db.add(essay)
    reading, listening = _reading_test(db), _reading_test(db, "listening")
    db.flush()
    for index in range(4):
        db.add(
            Mistake(
                user_id=1,
                submission_id=essay.id,
                skill="writing",
                category="grammar",
                subskill=f"sub-{index}",
                created_at=T0 + timedelta(minutes=30 * index + 5),
            )
        )
    # 12 attempts x 9 wrong answers per skill: ids pass 9 -> 10 and 99 -> 100 inside
    # one attempt, where the notebook's text order differs from the numeric one.
    for index in range(12):
        at = T0 + timedelta(minutes=30 * (index // 2))  # pairs of attempts share a timestamp
        _attempt(db, reading, at, wrong=set(range(9)))
        _attempt(db, listening, at, wrong=set(range(3, 12)))
    db.flush()
    wrong = db.query(AnswerRecord).filter(AnswerRecord.is_correct.is_(False)).order_by(AnswerRecord.id).all()
    for position, record in enumerate(wrong):
        if position % 3:
            name = record.attempt.test.test_type
            review = ("reviewing", "mastered")[position % 2]
            db.add(MistakeReview(user_id=1, skill=name, source_id=record.id, status=review))
    mistakes = db.query(Mistake).order_by(Mistake.id).all()
    db.add(MistakeReview(user_id=1, skill="writing", source_id=mistakes[0].id, status="mastered"))
    db.add(MistakeReview(user_id=1, skill="writing", source_id=mistakes[1].id, status="reviewing"))
    db.commit()


@pytest.mark.parametrize("skill", [None, "writing", "reading", "listening"])
@pytest.mark.parametrize("status", [None, "new", "reviewing", "mastered"])
def test_notebook_pages_match_the_unbounded_result(db, skill, status):
    _seed_notebook(db)
    expected = _notebook_reference(db, skill, status)
    assert expected

    for page, page_size in ((1, 20), (2, 20), (3, 7), (6, 20), (40, 20), (1, 100)):
        result = list_notebook(db, 1, skill, status, page, page_size)
        start = (page - 1) * page_size
        assert result["total"] == len(expected)
        got = [(item["id"], item["status"]) for item in result["items"]]
        assert got == [(item["id"], item["status"]) for item in expected[start : start + page_size]], (page, page_size)


def test_notebook_page_and_dashboard_summary_do_not_load_the_whole_notebook(db):
    _seed_notebook(db)
    reference = _notebook_reference(db, None, None)
    db.expire_all()
    records = _loads(AnswerRecord)
    try:
        summary = notebook_summary(db, 1)
        assert records["rows"] == 0  # counted in SQL: 216 wrong answers, none loaded
        page = list_notebook(db, 1, page=1, page_size=20)
    finally:
        records["stop"]()

    assert summary["total"] == len(reference) == 220
    for name in ("new", "reviewing", "mastered"):
        assert summary[name] == sum(item["status"] == name for item in reference)
    assert len(page["items"]) == 20 and page["total"] == 220
    assert records["rows"] <= 40  # at most page_size per objective skill


def test_notebook_items_keep_their_fields(db):
    reading = _reading_test(db)
    attempt = _attempt(db, reading, T0, wrong={0})
    listening = _reading_test(db, "listening")
    _attempt(db, listening, T0, wrong={1})
    db.commit()

    by_skill = {item["skill"]: item for item in list_notebook(db, 1)["items"]}

    item = by_skill["reading"]
    assert item["category"] == "matching" and item["label"] == "Matching" and item["status"] == "new"
    assert item["user_answer"] == "b" and item["correct_answer"] == "a"
    assert item["evidence"] == [{"paragraph": 1, "text": "Solar power is widely available."}]
    assert item["source_title"] == "reading test" and item["source_href"].endswith(str(attempt.id))
    assert by_skill["listening"]["category"] == "gist" and by_skill["listening"]["label"] == "Gist"


# ---- 3. Reading/Listening wrong answers feed the weakness model ----------------


def test_reading_and_listening_wrong_answers_become_weaknesses(db):
    reading, listening = _reading_test(db), _reading_test(db, "listening")
    now = utcnow()
    # Reading: all four "matching" questions wrong every time, one "true_false" slip once.
    for days in (3, 2, 1):
        _attempt(db, reading, now - timedelta(days=days), wrong={0, 3, 6, 9} | ({1} if days == 3 else set()))
    _attempt(db, reading, now, wrong=set())
    # Listening groups by target skill: indexes 0, 2, 4... are "detail".
    _attempt(db, listening, now, wrong={0, 2, 4, 6, 8, 10})
    db.commit()

    weaknesses = {(w["skill"], w["category"]): w for w in compute_weaknesses(db, 1, limit=10)}

    matching = weaknesses[("reading", "matching")]
    assert matching["label"] == "Matching" and matching["subskill"] == "matching"
    assert matching["frequency"] == 3 and matching["recent_frequency"] == 3 and matching["recurring"] is True
    assert matching["avg_severity"] == 3.0  # the whole group was wrong
    slip = weaknesses[("reading", "true_false")]
    assert slip["frequency"] == 1 and slip["avg_severity"] == 1.0 and slip["recurring"] is False
    assert slip["score"] < matching["score"]
    assert ("reading", "short_answer") not in weaknesses  # never answered wrong
    assert weaknesses[("listening", "detail")]["avg_severity"] == 3.0
    assert ("listening", "gist") not in weaknesses

    recurring = compute_recurring_mistakes(db, 1)
    assert [(r["skill"], r["category"], r["occurrences"], r["window"]) for r in recurring] == [
        ("reading", "matching", 3, 4)
    ]
    assert recurring[0]["message"] == "Matching in 3 of the last 4 attempts."

    # Derived at read time: nothing is stored, so the notebook still lists each wrong answer once.
    assert db.query(Mistake).count() == 0
    assert list_notebook(db, 1, page_size=100)["total"] == 3 * 4 + 1 + 6


def test_a_long_test_does_not_outweigh_an_essay(db):
    task = db.query(WritingTask).one()
    essay = WritingSubmission(user_id=1, task_id=task.id, text="t", word_count=1, status="graded", band=6.0)
    db.add(essay)
    reading = _reading_test(db)
    _attempt(db, reading, utcnow(), wrong=set(range(12)))
    db.flush()
    db.add(
        Mistake(user_id=1, submission_id=essay.id, skill="writing", category="grammar", subskill="articles", severity=3)
    )
    db.commit()

    scores = {(w["skill"], w["subskill"]): w["score"] for w in compute_weaknesses(db, 1, limit=10)}

    # Twelve wrong answers are three weak question groups, not twelve mistakes.
    assert scores[("reading", "matching")] == scores[("writing", "articles")]


# ---- 4. removed settings -------------------------------------------------------


def test_a_leftover_key_in_the_env_file_does_not_stop_startup(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "DATABASE_URL=postgresql://u:p@localhost/db\nSECRET_KEY=k\n"
        "GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback\nQUOTA_EXEMPT_USERS=student\n"
        "QUOTA_EXEMPT_USER_IDS=7\n"
    )

    loaded = Settings(_env_file=env)

    assert loaded.quota_exempt_user_ids == {7}
    assert not hasattr(loaded, "GOOGLE_REDIRECT_URI") and not hasattr(loaded, "QUOTA_EXEMPT_USERS")
