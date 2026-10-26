from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.infrastructure.logging import set_user_id
from app.infrastructure.ratelimit import RateLimiter
from app.infrastructure.security import JWTError, decode_access_token
from app.infrastructure.database import SessionLocal
from app.domain.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id, token_version = decode_access_token(token)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None or (user.token_version or 0) != token_version:
        raise credentials_exception
    set_user_id(user.id)
    return user


def user_rate_limit(name: str, max_requests: int, window_seconds: int = 60):
    """Dependency factory: cap a route per authenticated user (not per IP)."""
    limiter = RateLimiter(max_requests, window_seconds, name=name)

    def dependency(current_user: User = Depends(get_current_user)) -> None:
        limiter.check(f"user:{current_user.id}:{name}")

    return dependency
