import copy
import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.api.routers.listening import get_progress, list_listening_tests, review_listening, save_progress, submit_listening
from app.api.routers.tests import is_catalog_test
from app.api.schemas.listening import ListeningProgressIn, ListeningSubmitIn
from app.api.schemas.result import AnswerIn
from app.domain.models.attempt import Attempt, ListeningProgress
from app.domain.models.test import Test as ContentTest
from app.domain.models.user import User
from app.infrastructure.database import Base
from seed_listening import CONTENT_PATH, seed_package


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(id=1, username="student", password="hash"))
        session.commit()
        yield session
    engine.dispose()


def package(version):
    data = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))["tests"][0]
    data["content_version"] = version
    return data


def test_update_preserves_attempts_question_ids_and_in_progress_sessions(db):
    user = db.get(User, 1)
    old_data = package("1.0.0")
    old, _ = seed_package(db, old_data)
    question = old.sections[0].questions[0]
    question_id = question.id
    submitted = submit_listening(old.id, ListeningSubmitIn(
        content_version="1.0.0", mode="exam", submission_key="old-attempt-123",
        answers=[AnswerIn(question_id=question_id, answer="Hartley")],
    ), db=db, current_user=user)
    before = review_listening(submitted["attempt_id"], db=db, current_user=user)
    save_progress(old.id, ListeningProgressIn(
        content_version="1.0.0", mode="practice", answers={str(question_id): "Hartley"},
        current_section=0, audio_position=20, max_audio_position=20,
    ), db=db, current_user=user)
    data = package("1.0.1")
    data["sections"][0]["questions"][0]["explanation"] = "Updated explanation for future attempts."
    new, created = seed_package(db, data, update_existing=True)
    assert created and new.id != old.id
    assert new.sections[0].questions[0].id != question_id
    assert review_listening(submitted["attempt_id"], db=db, current_user=user) == before
    assert db.query(ListeningProgress).one().answers == {str(question_id): "Hartley"}
    assert [item["id"] for item in list_listening_tests(db=db, current_user=user)] == [new.id]
    assert is_catalog_test(new) and not is_catalog_test(old)
    # Old open tabs can still finish against their original question IDs/version.
    submit_listening(old.id, ListeningSubmitIn(
        content_version="1.0.0", mode="practice", submission_key="resumed-attempt-123",
        answers=[AnswerIn(question_id=question_id, answer="Hartley")],
    ), db=db, current_user=user)
    assert db.query(Attempt).count() == 2
    again, created = seed_package(db, data, update_existing=True)
    assert not created and again.id == new.id
    assert db.query(ContentTest).count() == 2


def test_update_requires_explicit_flag_and_rejects_downgrades(db):
    old, _ = seed_package(db, package("1.0.1"))
    kept, created = seed_package(db, package("1.0.2"))
    assert not created and kept.id == old.id
    with pytest.raises(ValueError, match="newer"):
        seed_package(db, package("1.0.0"), update_existing=True)
    assert db.query(ContentTest).count() == 1
    assert not old.content_metadata.get("superseded_by")


def test_invalid_update_does_not_hide_current_test(db):
    old, _ = seed_package(db, package("1.0.0"))
    broken = copy.deepcopy(package("1.0.1"))
    broken["sections"][0]["questions"].pop()
    with pytest.raises(ValueError, match="Invalid Listening"):
        seed_package(db, broken, update_existing=True)
    assert is_catalog_test(old)
    assert db.query(ContentTest).count() == 1


def test_progress_roundtrip_submission_review_and_user_isolation(db):
    user = db.get(User, 1)
    other = User(id=2, username="other", password="hash")
    db.add(other)
    db.commit()
    test, _ = seed_package(db, package("1.0.1"))
    question = test.sections[0].questions[0]
    payload = ListeningProgressIn(
        content_version=test.content_version, mode="practice",
        answers={str(question.id): "Hartley"}, current_section=2,
        audio_position=320, max_audio_position=350,
    )
    save_progress(test.id, payload, db=db, current_user=user)
    db.expire_all()
    restored = get_progress(test.id, test.content_version, "practice", db=db, current_user=user)
    assert restored.answers == payload.answers
    assert restored.current_section == 2
    assert restored.audio_position == 320
    assert restored.max_audio_position == 350
    assert get_progress(test.id, test.content_version, "practice", db=db, current_user=other) is None
    assert get_progress(test.id, test.content_version, "exam", db=db, current_user=user) is None
    submission = ListeningSubmitIn(
        content_version=test.content_version, mode="practice", submission_key="progress-roundtrip",
        answers=[AnswerIn(question_id=question.id, answer="Hartley")],
    )
    result = submit_listening(test.id, submission, db=db, current_user=user)
    db.expire_all()
    assert get_progress(test.id, test.content_version, "practice", db=db, current_user=user).status == "submitted"
    review = review_listening(result["attempt_id"], db=db, current_user=user)
    assert review["answers"][0]["user_answer"] == "Hartley"
    assert submit_listening(test.id, submission, db=db, current_user=user)["attempt_id"] == result["attempt_id"]
    assert db.query(Attempt).count() == 1
