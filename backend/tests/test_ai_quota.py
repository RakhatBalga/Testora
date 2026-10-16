import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.application.quota import quota_status, reserve_ai_call
from app.domain.models.ai_quota import AIQuotaBucket, AIReservation
from app.domain.models.speaking import SpeakingSubmission, SpeakingTask
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission
from app.infrastructure.config import settings
from app.infrastructure.database import Base


@pytest.fixture(params=["sqlite", "postgresql"])
def quota_engine(request, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AI_DAILY_ATTEMPTS", 20)
    monkeypatch.setattr(settings, "QUOTA_EXEMPT_USER_IDS", "")
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
        engine = create_engine(f"sqlite:///{tmp_path / 'quota.db'}", connect_args={"timeout": 15})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, username="student", password="hash"))
        db.commit()
    try:
        yield engine
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


@pytest.mark.parametrize("model,kind", [(WritingSubmission, "writing"), (SpeakingSubmission, "speaking")])
def test_parallel_requests_cannot_exceed_lifetime_budget(quota_engine, model, kind):
    barrier = threading.Barrier(8)
    def request(_):
        with Session(quota_engine) as db:
            user = db.get(User, 1)
            barrier.wait(timeout=10)
            try:
                with reserve_ai_call(db, user, kind, model=model, limit=2) as result:
                    result.success = True
                return 200
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(request, range(8)))
    assert outcomes.count(200) == 2
    assert outcomes.count(403) == 6
    with Session(quota_engine) as db:
        assert quota_status(db, model, db.get(User, 1), 2)["used"] == 2


def test_failures_refund_reviews_but_cannot_bypass_daily_budget(quota_engine, monkeypatch):
    monkeypatch.setattr(settings, "AI_DAILY_ATTEMPTS", 3)
    with Session(quota_engine) as db:
        user = db.get(User, 1)
        for _ in range(3):
            with reserve_ai_call(db, user, "writing", model=WritingSubmission, limit=1):
                pass  # Known provider failure.
        assert quota_status(db, WritingSubmission, user, 1)["used"] == 0
        with pytest.raises(HTTPException) as error:
            with reserve_ai_call(db, user, "writing", model=WritingSubmission, limit=1):
                pytest.fail("Exhausted daily budget must never call the provider")
        assert error.value.status_code == 429


def test_exception_refunds_and_releases_resource(quota_engine):
    with Session(quota_engine) as db:
        user = db.get(User, 1)
        with pytest.raises(RuntimeError):
            with reserve_ai_call(db, user, "writing", model=WritingSubmission, limit=1, resource="writing:1"):
                raise RuntimeError("provider failed")
        assert quota_status(db, WritingSubmission, user, 1)["used"] == 0
        assert db.query(AIReservation).one().active_resource is None
        with reserve_ai_call(db, user, "writing", model=WritingSubmission, limit=1, resource="writing:1") as result:
            result.success = True


def test_same_resource_cannot_run_in_two_sessions(quota_engine):
    with Session(quota_engine) as first, Session(quota_engine) as second:
        with reserve_ai_call(first, first.get(User, 1), "vocabulary", resource="word:1"):
            with pytest.raises(HTTPException) as error:
                with reserve_ai_call(second, second.get(User, 1), "vocabulary", resource="word:1"):
                    pytest.fail("Duplicate provider call")
            assert error.value.status_code == 409
        # A rejected duplicate did not consume an attempt.
        assert first.query(AIQuotaBucket).filter_by(kind="attempts").one().used == 1


def test_legacy_zero_band_speaking_consumes_quota(quota_engine):
    with Session(quota_engine) as db:
        task = SpeakingTask(part=1, questions=["Hello?"])
        db.add(task)
        db.flush()
        db.add(SpeakingSubmission(user_id=1, task_id=task.id, band=0, audio_url="test.webm"))
        db.commit()
        with pytest.raises(HTTPException) as error:
            with reserve_ai_call(db, db.get(User, 1), "speaking", model=SpeakingSubmission, limit=1):
                pytest.fail("Existing zero band review was ignored")
        assert error.value.status_code == 403


def test_username_exemption_cannot_be_claimed_by_renaming(quota_engine, monkeypatch):
    monkeypatch.setattr(settings, "QUOTA_EXEMPT_USERS", "student")
    with Session(quota_engine) as db:
        with pytest.raises(HTTPException):
            with reserve_ai_call(db, db.get(User, 1), "writing", model=WritingSubmission, limit=0):
                pytest.fail("Mutable username granted free AI")
