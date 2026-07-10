import secrets
import uuid
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import bcrypt
import httpx

from app.api.dependencies import get_current_user, get_db
from app.infrastructure.ratelimit import auth_rate_limit
from app.infrastructure.security import create_access_token
from app.infrastructure.config import settings
from app.domain.models.user import User
from app.api.schemas.auth import (
    GoogleAuthRequest,
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
    token = create_access_token({"sub": user.username})
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


@router.post(
    "/google",
    response_model=GoogleAuthResponse,
    dependencies=[Depends(auth_rate_limit)],
)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google auth is not configured")

    with httpx.Client() as client:
        token_res = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": payload.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": payload.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if token_res.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to exchange Google auth code")

    google_tokens = token_res.json()
    access_token = google_tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token from Google")

    with httpx.Client() as client:
        userinfo_res = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if userinfo_res.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to fetch Google user info")

    google_user = userinfo_res.json()
    google_id = google_user.get("id")
    email = google_user.get("email")
    name = google_user.get("name", "")

    if not google_id or not email:
        raise HTTPException(status_code=401, detail="Incomplete Google profile")

    user = db.query(User).filter(User.google_id == google_id).first()
    is_new_user = False
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
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

    token = create_access_token({"sub": user.username})
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

    The JWT subject is the username, so a successful change returns a fresh
    token — the old one would stop resolving to this user.
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
    token = create_access_token({"sub": current_user.username})
    return {"access_token": token, "token_type": "bearer"}
