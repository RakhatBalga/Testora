from sqlalchemy import Boolean, Column, DateTime, String

from app.infrastructure.database import Base


class OAuthFlow(Base):
    __tablename__ = "oauth_flows"

    state_hash = Column(String(64), primary_key=True)
    verifier = Column(String(128), nullable=False)
    redirect_uri = Column(String(2048), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed = Column(Boolean, nullable=False, default=False)
