from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from app.database import Base


class WritingTask(Base):
    __tablename__ = "writing_tasks"

    id = Column(Integer, primary_key=True)
    task_type = Column(Integer, nullable=False)  # 1 or 2
    title = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)  # chart/graph for Task 1
    min_words = Column(Integer, nullable=False, default=250)
    duration_minutes = Column(Integer, nullable=False, default=40)


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("writing_tasks.id"), nullable=False)
    text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="pending")  # pending | graded
    band = Column(Float, nullable=True)
    feedback = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("WritingTask")
