from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.infrastructure.database import Base


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="not_started")
    skills = Column(JSON, nullable=False, default=list)
    writing_submission_id = Column(Integer, nullable=True)
    reading_attempt_id = Column(Integer, nullable=True)
    provisional_level = Column(Float, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_diagnostic_sessions_user_started", "user_id", "started_at"),
    )


class StudyPlanItem(Base):
    __tablename__ = "study_plan_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    stable_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    minutes = Column(Integer, nullable=False)
    skill = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    href = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    scheduled_date = Column(Date, nullable=False)
    source_type = Column(String, nullable=False)
    source_ref = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "week_start", "stable_key", name="uq_study_plan_user_week_key"),
        Index("ix_study_plan_user_date", "user_id", "scheduled_date"),
        Index("ix_study_plan_user_status", "user_id", "status"),
    )


class MistakeReview(Base):
    __tablename__ = "mistake_reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill = Column(String, nullable=False)
    source_id = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="new")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "skill", "source_id", name="uq_mistake_review_source"),
        Index("ix_mistake_reviews_user_status", "user_id", "status"),
    )
