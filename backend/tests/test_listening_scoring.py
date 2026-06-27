from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routers.results import get_attempt, submit_attempt
from app.api.routers.listening import get_listening_test, review_listening, save_progress, submit_listening
from app.api.schemas.listening import ListeningProgressIn, ListeningSubmitIn
from app.api.schemas.result import AnswerIn, SubmitIn
from app.domain.band import band_from_raw
from app.domain.listening_scoring import answer_word_count, grade_listening
from app.domain.models.attempt import Attempt, ListeningProgress
from app.domain.models.test import Question, Section, Test as ContentTest
from app.domain.models.user import User
from app.infrastructure.database import Base


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_listening_band_mapping_uses_listening_thresholds():
    assert band_from_raw(32, 40, "listening") == 7.5
    assert band_from_raw(32, 40, "reading") == 7.0
    assert band_from_raw(39, 40, "listening") == 9.0


def test_listening_attempt_is_scored_stored_and_reviewable():
    db = _db()
    try:
        user = User(username="listener", password="hashed")
        test = ContentTest(title="Listening test", test_type="listening", duration_minutes=30)
        section = Section(order=1, title="Section 1", passage="The room is on King Street.")
        section.questions = [
            Question(order=1, text="Street", question_type="fill_blank", correct_answer=["King Street"], explanation="The speaker names King Street."),
            Question(order=2, text="Day", question_type="single_choice", options=["Monday", "Tuesday"], correct_answer=["Tuesday"], explanation="The appointment is Tuesday."),
        ]
        test.sections = [section]
        db.add_all([user, test])
        db.commit()

        payload = SubmitIn(
            test_id=test.id,
            answers=[
                AnswerIn(question_id=section.questions[0].id, answer="king street"),
                AnswerIn(question_id=section.questions[1].id, answer="Monday", marked_for_review=True),
            ],
            duration_seconds=95,
        )
        submitted = submit_attempt(payload, db=db, current_user=user)
        reviewed = get_attempt(submitted["id"], db=db, current_user=user)

        assert submitted["score"] == 1
        assert submitted["total"] == 2
        assert submitted["band"] == 5.5
        assert submitted["breakdown"][0]["accuracy"] == 0
        assert reviewed["answers"][1]["marked_for_review"] is True
        assert reviewed["answers"][1]["explanation"] == "The appointment is Tuesday."
    finally:
        db.close()


def _published_test(db):
    test = ContentTest(
        title="Testora Listening",
        test_type="listening",
        duration_minutes=12,
        content_version="1.0.0",
        content_metadata={"published": True, "calibration_status": "provisional"},
    )
    section = Section(
        order=1,
        title="Section 1",
        passage="Guide: The workshop is on King Street.",
        audio_url="/static/audio/listening/test.m4a",
        section_metadata={
            "audio_start": 10.0,
            "audio_end": 30.0,
            "transcript_segments": [{"id": "s1-01", "speaker": "Guide", "text": "The workshop is on King Street.", "start": 10.0, "end": 12.0}],
        },
    )
    section.questions = [Question(
        order=1,
        text="Street",
        question_type="fill_blank",
        correct_answer=["King Street"],
        explanation="The guide names King Street.",
        evidence=[{"paragraph": 1, "text": "King Street"}],
        question_metadata={"word_limit": 2, "target_skill": "detail", "evidence_segment": "s1-01"},
    )]
    test.sections = [section]
    db.add(test)
    db.commit()
    return test


def test_public_payload_redacts_transcript_answers_and_evidence():
    db = _db()
    try:
        user = User(username="public-listener", password="hashed")
        db.add(user)
        test = _published_test(db)
        payload = get_listening_test(test.id, db=db, current_user=user)

        assert "passage" not in payload["sections"][0]
        assert "transcript_segments" not in payload["sections"][0]
        assert "correct_answer" not in payload["sections"][0]["questions"][0]
        assert "evidence" not in payload["sections"][0]["questions"][0]
    finally:
        db.close()


def test_listening_word_limit_is_strict_and_hyphenated_word_counts_once():
    question = SimpleNamespace(
        id=1,
        text="Street",
        question_type="fill_blank",
        correct_answer=["King Street"],
        explanation="Named in audio",
        question_metadata={"word_limit": 2},
    )
    _, valid_score, _ = grade_listening([question], {1: "King Street"})
    _, invalid_score, _ = grade_listening([question], {1: "the King Street"})

    assert valid_score == 1
    assert invalid_score == 0
    assert answer_word_count("forty-two") == 1


def test_submit_is_idempotent_and_review_requires_owner():
    db = _db()
    try:
        user = User(username="owner", password="hashed")
        stranger = User(username="stranger", password="hashed")
        db.add_all([user, stranger])
        test = _published_test(db)
        payload = ListeningSubmitIn(
            content_version="1.0.0",
            mode="exam",
            submission_key="attempt-key-123",
            answers=[AnswerIn(question_id=test.sections[0].questions[0].id, answer="King Street")],
            duration_seconds=60,
        )
        first = submit_listening(test.id, payload, db=db, current_user=user)
        second = submit_listening(test.id, payload, db=db, current_user=user)

        assert first["attempt_id"] == second["attempt_id"]
        assert db.query(Attempt).count() == 1
        review = review_listening(first["attempt_id"], db=db, current_user=user)
        assert review["answers"][0]["evidence"][0]["start"] == 10.0
        with pytest.raises(Exception) as error:
            review_listening(first["attempt_id"], db=db, current_user=stranger)
        assert error.value.status_code == 404
    finally:
        db.close()


def test_progress_updates_existing_versioned_session():
    db = _db()
    try:
        user = User(username="progress-listener", password="hashed")
        db.add(user)
        test = _published_test(db)
        payload = ListeningProgressIn(
            content_version="1.0.0",
            mode="practice",
            answers={"1": "King"},
            current_section=0,
            audio_position=12.5,
            max_audio_position=12.5,
        )
        first = save_progress(test.id, payload, db=db, current_user=user)
        payload.audio_position = 14.0
        second = save_progress(test.id, payload, db=db, current_user=user)

        assert first.id == second.id
        assert second.max_audio_position == 14.0
        assert db.query(ListeningProgress).count() == 1
    finally:
        db.close()
