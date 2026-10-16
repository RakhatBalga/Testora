from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.infrastructure.config import settings


def create_access_token(user_id: int) -> str:
    # Versioning rejects legacy username subjects, including numeric usernames.
    to_encode = {"sub": str(user_id), "version": 2, "type": "access"}
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def access_token_user_id(token: str) -> int:
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
        options={"require_exp": True, "require_iat": True, "require_sub": True},
    )
    subject = payload["sub"]
    if (payload.get("version") != 2 or payload.get("type") != "access"
            or not isinstance(subject, str) or not subject.isascii()
            or not subject.isdecimal() or subject.startswith("0")):
        raise JWTError("Invalid access token subject or version")
    return int(subject)
