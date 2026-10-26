from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String
from app.infrastructure.database import Base
from app.infrastructure.time import utcnow


class StoredFile(Base):
    """Binary upload (avatar, speaking audio) kept in Postgres so it survives
    restarts of hosts with ephemeral disks. Size is capped at upload time."""

    __tablename__ = "stored_files"

    id = Column(String(32), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(24), nullable=False)  # avatar | speaking_audio
    content_type = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
