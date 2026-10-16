import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import bcrypt
import httpx

from app.api.dependencies import get_current_user, get_db
from app.infrastructure.ratelimit import auth_rate_limit
from app.infrastructure.security import create_access_token
from app.infrastructure.config import settings
from app.domain.models.user import User
from app.application.oauth import consume_flow, start_flow
from app.api.schemas.auth import (
    GoogleAuthRequest,
    GoogleStartRequest,
    GoogleAuthResponse,
    LoginRequest,
    RegisterRequest,
    SetUsernameRequest,
    TokenResponse,
    UserProfileOut,
    UserProfileUpdate,
)

router = APIRouter()


@router.post("/register", dependencies=[Depends(auth_rate_limit)])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt())
    new_user = User(
        username=payload.username,
        password=hashed_password.decode("utf-8"),
        target_band=payload.target_band,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent registrations of the same username race past the check
        # above; the unique constraint catches it — return a clean 400, not 500.
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already taken")
    return {"message": f"User {payload.username} registered successfully"}


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not bcrypt.checkpw(
        payload.password.encode("utf-8"), user.password.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


# Avatar images are public, low-risk assets served straight from /static.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
AVATAR_DIR = _BACKEND_ROOT / "static" / "avatars"
_AVATAR_URL_PREFIX = "/static/avatars/"
_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_AVATAR_BYTES = settings.MAX_AVATAR_UPLOAD_MB * 1024 * 1024
_AVATAR_CHUNK = 512 * 1024  # 512 KiB


def _remove_avatar_file(avatar: str | None) -> None:
    """Delete a previously uploaded avatar file, if any. Best-effort."""
    if not avatar or not avatar.startswith(_AVATAR_URL_PREFIX):
        return
    old = AVATAR_DIR / Path(avatar).name
    try:
        old.unlink(missing_ok=True)
    except OSError:
        pass


@router.get("/me", response_model=UserProfileOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/me/avatar", response_model=UserProfileOut)
def upload_avatar(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in _AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Avatar must be a JPG, PNG, WEBP, or GIF image.",
        )

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"user{current_user.id}_{uuid.uuid4().hex}{suffix}"
    path = AVATAR_DIR / filename

    # Stream to disk with a hard size ceiling so a huge upload can't exhaust
    # memory or disk. Abort and clean up if exceeded.
    written = 0
    try:
        with path.open("wb") as buffer:
            while chunk := image.file.read(_AVATAR_CHUNK):
                written += len(chunk)
                if written > _MAX_AVATAR_BYTES:
                    buffer.close()
                    path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Avatar exceeds the {settings.MAX_AVATAR_UPLOAD_MB} MB limit.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    if written == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty image upload.")

    _remove_avatar_file(current_user.avatar)
    current_user.avatar = f"{_AVATAR_URL_PREFIX}{filename}"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me/avatar", response_model=UserProfileOut)
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _remove_avatar_file(current_user.avatar)
    current_user.avatar = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me", response_model=UserProfileOut)
def update_me(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fields = payload.model_dump(exclude_unset=True)
    if "target_band" in fields and fields["target_band"] is None:
        raise HTTPException(status_code=422, detail="Target band cannot be empty")
    target = fields.get("target_band", current_user.target_band)
    current = fields.get("current_level", current_user.current_level)
    if current is not None and target < current:
        raise HTTPException(
            status_code=422,
            detail="Target band must be greater than or equal to current level",
        )
    for field, value in fields.items():
        setattr(current_user, field, value)
    if "current_level" in fields:
        current_user.current_level_source = "self_reported" if fields["current_level"] else None
    db.add(current_user)
    if fields.keys() & {
        "target_band",
        "current_level",
        "exam_date",
        "weekly_study_days",
        "daily_study_minutes",
        "primary_focus",
    }:
        from app.application.learning.study_plan import get_weekly_plan

        get_weekly_plan(db, current_user, recalculate=True)
    else:
        db.commit()
    db.refresh(current_user)
    return current_user


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _google_request(method: str, url: str, **kwargs) -> dict:
    """Map provider failures to actionable messages without exposing responses."""
    try:
        with httpx.Client(timeout=15) as client:
            response = client.request(method, url, **kwargs)
    except httpx.TimeoutException:
        raise HTTPException(504, "Google took too long to respond. Please start sign-in again.") from None
    except httpx.RequestError:
        raise HTTPException(503, "Google sign-in is temporarily unavailable. Please try again.") from None
    if response.status_code == 429 or response.status_code >= 500:
        raise HTTPException(503, "Google sign-in is temporarily unavailable. Please try again.")
    if response.status_code != 200:
        raise HTTPException(400, "Google could not complete sign-in. Please start again.")
    try:
        payload = response.json()
    except ValueError:
        raise HTTPException(502, "Google returned an invalid response. Please start sign-in again.") from None
    if not isinstance(payload, dict):
        raise HTTPException(502, "Google returned an invalid response. Please start sign-in again.")
    return payload


@router.post("/google/start", dependencies=[Depends(auth_rate_limit)])
def google_start(payload: GoogleStartRequest, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google auth is not configured")
    return {"authorization_url": start_flow(db, payload.state, payload.redirect_uri)}


@router.post(
    "/google",
    response_model=GoogleAuthResponse,
    dependencies=[Depends(auth_rate_limit)],
)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google auth is not configured")

    verifier = consume_flow(db, payload.state, payload.redirect_uri)
    google_tokens = _google_request("POST", GOOGLE_TOKEN_URL, data={
        "code": payload.code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": payload.redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    })
    access_token = google_tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token from Google")

    google_user = _google_request("GET", GOOGLE_USERINFO_URL,
                                  headers={"Authorization": f"Bearer {access_token}"})
    google_id = google_user.get("id")
    email = google_user.get("email")
    if not google_id or not email or google_user.get("verified_email") is not True:
        raise HTTPException(status_code=401, detail="Incomplete Google profile")

    user = db.query(User).filter(User.google_id == google_id).first()
    is_new_user = False
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            if user.google_id and user.google_id != google_id:
                raise HTTPException(status_code=409, detail="Email is linked to another Google account")
            user.google_id = google_id
            db.commit()

    if not user:
        # Prefer the nickname chosen in the register flow; fall back to the
        # email prefix. Either way, de-collide with a numeric suffix.
        base_username = (payload.username or email.split("@")[0]).strip()
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        dummy_password = bcrypt.hashpw(
            secrets.token_bytes(32), bcrypt.gensalt()
        ).decode("utf-8")
        user = User(
            username=username,
            password=dummy_password,
            email=email,
            google_id=google_id,
            target_band=payload.target_band or 7.5,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new_user = True

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "is_new_user": is_new_user,
        "username": user.username,
    }


@router.post("/username", response_model=TokenResponse)
def set_username(
    payload: SetUsernameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the account username (e.g. after Google signup).

    Tokens remain bound to the immutable user ID after a rename.
    """
    taken = (
        db.query(User)
        .filter(User.username == payload.username, User.id != current_user.id)
        .first()
    )
    if taken:
        raise HTTPException(status_code=400, detail="Username already taken")
    current_user.username = payload.username
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already taken")
    token = create_access_token(current_user.id)
    return {"access_token": token, "token_type": "bearer"}
