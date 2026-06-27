from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routers.results import get_attempt, submit_attempt
from app.api.schemas.result import AnswerIn, SubmitIn
from app.domain.band import band_from_raw
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
