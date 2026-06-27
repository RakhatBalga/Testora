from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.analytics.band_gap import generate_blockers
from app.application.analytics.recommendations import compute_recommendations
from app.domain.models.attempt import Attempt
from app.domain.models.test import Question, Section, Test as ContentTest
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure.database import Base


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_task_response_blocker_recommends_task_two():
    db = _session()
    try:
        user = User(username="writer", password="hashed")
        task = WritingTask(task_type=2, title="Essay", prompt="Discuss.", min_words=250, duration_minutes=40)
        db.add_all([user, task])
        db.flush()
        db.add(WritingSubmission(
            user_id=user.id,
            task_id=task.id,
            text="essay",
            word_count=250,
            status="graded",
            band=6.5,
            feedback={"criteria": {"Task Response": 6.0, "Lexical Resource": 7.0}},
        ))
        db.commit()

        blocker = generate_blockers(db, user.id, target=7.5, limit=1)[0]

        assert blocker["criterion"] == "Task Response"
        assert blocker["fix_href"] == "/writing?task=2"
    finally:
        db.close()


def test_question_type_recommendation_links_to_matching_listening_test():
    db = _session()
    try:
        user = User(username="listener", password="hashed")
        listening = ContentTest(title="Listening A", test_type="listening", duration_minutes=30)
        section = Section(order=1, title="Section 1")
        section.questions = [Question(order=1, text="Heading", question_type="matching_information", correct_answer=["A"])]
        listening.sections = [section]
        db.add_all([user, listening])
        db.flush()
        db.add(Attempt(
            user_id=user.id,
            test_id=listening.id,
            score=20,
            total=40,
            band=5.5,
            breakdown=[{"question_type": "matching_information", "label": "Matching Information", "correct": 0, "total": 5, "accuracy": 0}],
        ))
        db.commit()

        recs = compute_recommendations(db, user.id, target=7.5, limit=5)
        question_type_rec = next(rec for rec in recs if rec["source"] == "question_type")

        assert question_type_rec["href"] == f"/listening/{listening.id}"
        assert question_type_rec["title"] == "Drill Matching Information"
    finally:
        db.close()
