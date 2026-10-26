from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.routers.speaking import _resolve_media_user
from app.domain.models.user import User
from app.infrastructure.config import settings
from app.infrastructure.database import Base
from app.infrastructure.security import create_access_token


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.mark.parametrize("resolve", [get_current_user, _resolve_media_user])
def test_rename_and_username_reuse_never_transfer_token(db, resolve):
    owner = User(username="original", password="hash")
    db.add(owner)
    db.commit()
    token = create_access_token(owner.id)
    owner.username = "renamed"
    db.commit()
    other = User(username="original", password="hash")
    db.add(other)
    db.commit()
    assert resolve(token=token, db=db).id == owner.id
    db.delete(owner)
    db.commit()
    with pytest.raises(HTTPException) as error:
        resolve(token=token, db=db)
    assert error.value.status_code == 401


@pytest.mark.parametrize("claims", [
    {"sub": "1"},  # Legacy numeric username must not become user ID 1.
    {"sub": "original"},
    {"sub": "01", "version": 2, "type": "access"},
    {"sub": "-1", "version": 2, "type": "access"},
    {"sub": "1", "version": 2, "type": "refresh"},
    {"sub": "1", "version": 2, "type": "access", "exp": 1},
])
@pytest.mark.parametrize("resolve", [get_current_user, _resolve_media_user])
def test_invalid_or_legacy_claims_are_rejected(db, claims, resolve):
    db.add(User(id=1, username="original", password="hash"))
    db.commit()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"iat": now, "exp": now + timedelta(minutes=5), **claims},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )
    with pytest.raises(HTTPException) as error:
        resolve(token=token, db=db)
    assert error.value.status_code == 401


def test_expiration_is_required(db):
    token = jwt.encode({"sub": "1", "version": 2, "type": "access", "iat": 1},
                       settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException):
        get_current_user(token=token, db=db)
