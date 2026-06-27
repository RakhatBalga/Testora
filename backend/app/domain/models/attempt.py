from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base


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
    content_version = Column(String, nullable=False, default="legacy")
    mode = Column(String, nullable=False, default="exam")
    submission_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    test = relationship("Test")
    answers = relationship(
        "AnswerRecord", back_populates="attempt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_attempts_user_created", "user_id", "created_at"),
        UniqueConstraint("user_id", "test_id", "submission_key", name="uq_attempt_submission_key"),
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


class ListeningProgress(Base):
    __tablename__ = "listening_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    content_version = Column(String, nullable=False)
    mode = Column(String, nullable=False, default="practice")
    answers = Column(JSON, nullable=False, default=dict)
    current_section = Column(Integer, nullable=False, default=0)
    audio_position = Column(Float, nullable=False, default=0)
    max_audio_position = Column(Float, nullable=False, default=0)
    status = Column(String, nullable=False, default="in_progress")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "test_id", "content_version", "mode",
            name="uq_listening_progress_user_test_version_mode",
        ),
        Index("ix_listening_progress_user_updated", "user_id", "updated_at"),
    )
