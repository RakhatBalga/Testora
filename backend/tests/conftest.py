"""Test fixtures and environment.

Settings require DATABASE_URL/SECRET_KEY at import; set throwaway values before
the app package is imported so unit tests don't need a real database. The Gemini
tests never open a DB connection — they exercise the grading logic in isolation.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-for-anything-real")
os.environ.setdefault("AI_PROVIDER", "mock")


import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture()
def api(monkeypatch, tmp_path):
    """TestClient on the real app, backed by an in-memory SQLite database.

    Yields a namespace with `.client`, `.Session` (a session factory on the same
    database), `.user` (a registered user) and `.headers` (its bearer token).
    """
    from types import SimpleNamespace

    from app.api.dependencies import get_db
    from app.domain.models.user import User
    from app.infrastructure import ratelimit, storage
    from app.infrastructure.config import settings
    from app.infrastructure.database import Base
    from app.infrastructure.security import create_access_token
    from app.main import app

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "database")
    monkeypatch.setattr(storage, "PRIVATE_AUDIO_DIR", tmp_path / "audio")
    monkeypatch.setattr(storage, "AVATAR_DIR", tmp_path / "avatars")
    monkeypatch.setattr(ratelimit, "_first_proxied_request_logged", False)
    ratelimit.reset_all_limiters()
    with Session() as db:
        user = User(username="student", password="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(user.id)
        user_id = user.id
    ns = SimpleNamespace(
        client=TestClient(app),
        Session=Session,
        user_id=user_id,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        yield ns
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
