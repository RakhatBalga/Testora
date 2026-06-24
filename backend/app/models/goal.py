from datetime import datetime

from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey

from app.database import Base


class Goal(Base):
    """The user's IELTS goal — captured at onboarding, read by the band-gap engine.

    One row per user (``user_id`` unique). ``target_band`` is the destination the
    band gap is measured against; ``current_band`` is an optional self-estimate used
    as a fallback until the user has graded attempts; ``exam_date`` drives the
    dashboard countdown.
    """

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    target_band = Column(Float, nullable=False)
    current_band = Column(Float, nullable=True)  # self-estimate fallback
    exam_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
