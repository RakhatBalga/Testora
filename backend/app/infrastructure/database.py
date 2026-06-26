from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.infrastructure.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    # Verify a connection is alive before using it, so a DB restart or dropped
    # idle connection surfaces as a transparent reconnect instead of an error.
    pool_pre_ping=True,
    # Recycle connections before common 30-minute server/proxy idle timeouts.
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass