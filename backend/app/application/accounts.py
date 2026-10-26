"""Account use cases: registration, login, profile, avatar, logout."""

import bcrypt
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models.user import User
from app.infrastructure.security import create_access_token
from app.infrastructure.storage import DB_PREFIX, get_storage, storage_for_key
from app.infrastructure.storage.sniff import sniff_image

DB_AVATAR_URL_PREFIX = "/auth/avatars/"
LOCAL_AVATAR_URL_PREFIX = "/static/avatars/"


def register(db: Session, username: str, password: str, target_band: float) -> None:
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    db.add(User(username=username, password=hashed.decode("utf-8"), target_band=target_band))
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent registrations of the same username race past the check
        # above; the unique constraint catches it: clean 400, not 500.
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already taken")


def login(db: Session, username: str, password: str) -> str:
    user = db.query(User).filter(User.username == username).first()
    # bcrypt reads at most 72 bytes; truncating explicitly keeps accounts created
    # before the byte check working on bcrypt versions that would raise instead.
    if not user or not bcrypt.checkpw(password.encode("utf-8")[:72], user.password.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return create_access_token(user.id, user.token_version or 0)


def logout(db: Session, user: User) -> None:
    """Revoke every access token issued so far for this account."""
    user.token_version = (user.token_version or 0) + 1
    db.commit()


def change_username(db: Session, user: User, username: str) -> str:
    taken = db.query(User).filter(User.username == username, User.id != user.id).first()
    if taken:
        raise HTTPException(status_code=400, detail="Username already taken")
    user.username = username
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already taken")
    return create_access_token(user.id, user.token_version or 0)


_PLAN_FIELDS = {
    "target_band",
    "current_level",
    "exam_date",
    "weekly_study_days",
    "daily_study_minutes",
    "primary_focus",
}


def update_profile(db: Session, user: User, fields: dict) -> User:
    if "target_band" in fields and fields["target_band"] is None:
        raise HTTPException(status_code=422, detail="Target band cannot be empty")
    target = fields.get("target_band", user.target_band)
    current = fields.get("current_level", user.current_level)
    if current is not None and target < current:
        raise HTTPException(status_code=422, detail="Target band must be greater than or equal to current level")
    for field, value in fields.items():
        setattr(user, field, value)
    if "current_level" in fields:
        user.current_level_source = "self_reported" if fields["current_level"] else None
    db.add(user)
    if fields.keys() & _PLAN_FIELDS:
        from app.application.learning.study_plan import get_weekly_plan

        get_weekly_plan(db, user, recalculate=True)
    else:
        db.commit()
    db.refresh(user)
    return user


def _avatar_key(avatar: str | None) -> str | None:
    if not avatar:
        return None
    if avatar.startswith(DB_AVATAR_URL_PREFIX):
        return DB_PREFIX + avatar[len(DB_AVATAR_URL_PREFIX) :]
    if avatar.startswith(LOCAL_AVATAR_URL_PREFIX):
        return avatar[len(LOCAL_AVATAR_URL_PREFIX) :]
    return None


def _remove_avatar(db: Session, avatar: str | None) -> None:
    key = _avatar_key(avatar)
    if key:
        storage_for_key(key).delete(db, key)


def set_avatar(db: Session, user: User, data: bytes) -> User:
    content_type = sniff_image(data[:16])
    if content_type is None:
        raise HTTPException(status_code=400, detail="Avatar must be a JPG, PNG, WEBP, or GIF image.")
    storage = get_storage()
    key = storage.save(db, kind="avatar", owner_id=user.id, data=data, content_type=content_type)
    previous = user.avatar
    user.avatar = (
        DB_AVATAR_URL_PREFIX + key[len(DB_PREFIX) :] if key.startswith(DB_PREFIX) else LOCAL_AVATAR_URL_PREFIX + key
    )
    db.add(user)
    _remove_avatar(db, previous)
    db.commit()
    db.refresh(user)
    return user


def delete_avatar(db: Session, user: User) -> User:
    _remove_avatar(db, user.avatar)
    user.avatar = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def load_avatar(db: Session, avatar_id: str):
    if not avatar_id.isalnum() or len(avatar_id) != 32:
        return None
    blob = storage_for_key(DB_PREFIX + avatar_id).load(db, DB_PREFIX + avatar_id)
    return blob if blob and blob.content_type.startswith("image/") else None
