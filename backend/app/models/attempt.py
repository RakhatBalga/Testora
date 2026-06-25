from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    band = Column(Float, nullable=True)
    # Seconds the user spent on the test (null for legacy attempts).
    duration_seconds = Column(Integer, nullable=True)
    # Per-question-type performance breakdown, computed at submit time.
    breakdown = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    test = relationship("Test")
    answers = relationship(
        "AnswerRecord", back_populates="attempt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_attempts_user_created", "user_id", "created_at"),
    )


class AnswerRecord(Base):
    __tablename__ = "answer_records"

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)
    marked_for_review = Column(Boolean, nullable=False, default=False)

    attempt = relationship("Attempt", back_populates="answers")
    question = relationship("Question")
