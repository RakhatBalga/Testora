from sqlalchemy import Boolean, Column, Date, Float, Integer, String
from app.infrastructure.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    target_band = Column(Float, nullable=False, default=7.5)
    current_level = Column(Float, nullable=True)
    current_level_source = Column(String, nullable=True)
    exam_date = Column(Date, nullable=True)
    weekly_study_days = Column(Integer, nullable=False, default=3)
    daily_study_minutes = Column(Integer, nullable=False, default=30)
    primary_focus = Column(String, nullable=False, default="balanced")
    onboarding_completed = Column(Boolean, nullable=False, default=False)
