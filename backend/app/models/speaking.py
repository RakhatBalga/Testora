from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from app.database import Base


class SpeakingTask(Base):
    __tablename__ = "speaking_tasks"

    id = Column(Integer, primary_key=True)
    part = Column(Integer, nullable=False)  # 1, 2, or 3
    questions = Column(JSON, nullable=False)
    prep_seconds = Column(Integer, nullable=False, default=60)
    speak_seconds = Column(Integer, nullable=False, default=120)


class SpeakingSubmission(Base):
    __tablename__ = "speaking_submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("speaking_tasks.id"), nullable=False)
    audio_url = Column(String, nullable=False)
    transcript = Column(String, nullable=True)
    band = Column(Float, nullable=True)
    feedback = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("SpeakingTask")
