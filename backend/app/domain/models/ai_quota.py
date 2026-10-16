from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, func
from app.infrastructure.database import Base


class AIQuotaBucket(Base):
    __tablename__ = "ai_quota_buckets"
    __table_args__ = (CheckConstraint("used >= 0", name="ck_ai_quota_used"),)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    kind = Column(String(32), primary_key=True)
    period = Column(String(16), primary_key=True)
    used = Column(Integer, nullable=False)


class AIReservation(Base):
    __tablename__ = "ai_reservations"
    id = Column(String(32), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    active_resource = Column(String(160), nullable=True, unique=True)
    status = Column(String(16), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
