from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index

from app.database import Base


class Mistake(Base):
    """An atomic mistake captured at grading time.

    `submission_id` is a polymorphic reference (writing_submissions /
    speaking_submissions / attempts) disambiguated by `skill` — there is no FK
    because the source table varies. Analytics aggregates these rows; it never
    calls the AI layer.
    """

    __tablename__ = "mistakes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submission_id = Column(Integer, nullable=True)

    skill = Column(String, nullable=False)      # writing | speaking | reading | listening
    category = Column(String, nullable=False)   # grammar | vocabulary | coherence | task_response | ...
    subskill = Column(String, nullable=True)    # articles | paragraphing | answer_length | ...
    severity = Column(Integer, nullable=False, default=1)  # 1..3

    snippet = Column(Text, nullable=True)
    correction = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_mistakes_user_category", "user_id", "category"),
        Index("ix_mistakes_user_created", "user_id", "created_at"),
        Index("ix_mistakes_user_skill", "user_id", "skill"),
    )
