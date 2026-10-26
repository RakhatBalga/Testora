from datetime import datetime, timedelta, timezone

import jwt
from jwt import PyJWTError as JWTError  # noqa: F401 - re-exported for callers

from app.infrastructure.config import settings


def create_access_token(user_id: int, token_version: int = 0) -> str:
    # Versioning rejects legacy username subjects, including numeric usernames.
    # "tv" is the user's session counter: bumping it (logout) revokes old tokens.
    to_encode = {"sub": str(user_id), "version": 2, "type": "access", "tv": token_version}
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> tuple[int, int]:
    """Return (user_id, token_version); raises JWTError for any invalid token."""
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
        options={"require": ["exp", "iat", "sub"]},
    )
    subject = payload["sub"]
    token_version = payload.get("tv", 0)
    if (payload.get("version") != 2 or payload.get("type") != "access"
            or not isinstance(subject, str) or not subject.isascii()
            or not subject.isdecimal() or subject.startswith("0")
            or not isinstance(token_version, int) or isinstance(token_version, bool)):
        raise JWTError("Invalid access token subject or version")
    return int(subject), token_version


def access_token_user_id(token: str) -> int:
    return decode_access_token(token)[0]
