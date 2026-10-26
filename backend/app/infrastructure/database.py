from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.infrastructure.config import settings

_connect_args: dict = {}
_pool_args: dict = {}
if settings.DATABASE_URL.startswith("postgresql"):
    _pool_args = {"pool_timeout": settings.DB_POOL_TIMEOUT_SECONDS}
    # psycopg2 has no timeouts by default, so a hung Neon wake-up would block a
    # worker thread forever.
    _connect_args = {"connect_timeout": settings.DB_CONNECT_TIMEOUT_SECONDS}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    **_pool_args,
    # Verify a connection is alive before using it, so a DB restart or dropped
    # idle connection surfaces as a transparent reconnect instead of an error.
    pool_pre_ping=True,
    # Recycle connections before common 30-minute server/proxy idle timeouts.
    pool_recycle=1800,
)

if settings.DATABASE_URL.startswith("postgresql"):

    @event.listens_for(engine, "connect")
    def _set_statement_timeout(dbapi_connection, _record):
        # Sent as a SET instead of a startup "options" parameter, because
        # Neon's pooled (pgbouncer) endpoint rejects unknown startup options.
        try:
            with dbapi_connection.cursor() as cursor:
                cursor.execute(f"SET statement_timeout = {int(settings.DB_STATEMENT_TIMEOUT_MS)}")
            dbapi_connection.commit()
        except Exception:  # noqa: BLE001 - a failed SET must not block connecting
            dbapi_connection.rollback()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass