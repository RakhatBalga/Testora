from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.analytics.weekly import compute_weekly_weakest
from app.domain.models.attempt import Attempt
from app.domain.models.speaking import SpeakingSubmission, SpeakingTask
from app.domain.models.test import Test as ContentTest
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure.database import Base


def test_weekly_weakest_uses_only_recent_graded_events():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        user = User(username="student", password="hashed")
        writing_task = WritingTask(task_type=2, title="Essay", prompt="Prompt", min_words=250, duration_minutes=40)
        speaking_task = SpeakingTask(part=2, questions=["Describe a place"], prep_seconds=60, speak_seconds=120)
        listening = ContentTest(title="Listening", test_type="listening", duration_minutes=30)
        reading = ContentTest(title="Reading", test_type="reading", duration_minutes=60)
        db.add_all([user, writing_task, speaking_task, listening, reading])
        db.flush()
        now = datetime.utcnow()
        db.add_all([
            WritingSubmission(user_id=user.id, task_id=writing_task.id, text="x", word_count=1, status="graded", band=7.0, created_at=now),
            SpeakingSubmission(user_id=user.id, task_id=speaking_task.id, audio_url="a.webm", band=6.5, created_at=now - timedelta(days=2)),
            Attempt(user_id=user.id, test_id=listening.id, score=24, total=40, band=6.0, created_at=now - timedelta(days=1)),
            Attempt(user_id=user.id, test_id=reading.id, score=10, total=40, band=4.0, created_at=now - timedelta(days=8)),
        ])
        db.commit()

        result = compute_weekly_weakest(db, user.id)

        assert result == {"has_data": True, "skill": "listening", "band": 6.0, "attempts": 1, "days": 7}
    finally:
        db.close()
