from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, user_rate_limit
from app.api.uploads import read_capped
from app.application import accounts, google_auth
from app.infrastructure.ratelimit import auth_rate_limit
from app.infrastructure.config import settings
from app.domain.models.user import User
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
    accounts.register(db, payload.username, payload.password, payload.target_band)
    return {"message": f"User {payload.username} registered successfully"}


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return {"access_token": accounts.login(db, payload.username, payload.password), "token_type": "bearer"}


@router.post("/logout", status_code=204)
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sign out everywhere: tokens issued before this call stop working."""
    accounts.logout(db, current_user)
    return Response(status_code=204)


@router.get("/me", response_model=UserProfileOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post(
    "/me/avatar",
    response_model=UserProfileOut,
    dependencies=[Depends(user_rate_limit("avatar-upload", 10))],
)
def upload_avatar(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = read_capped(image, settings.MAX_AVATAR_UPLOAD_MB, "Avatar")
    return accounts.set_avatar(db, current_user, data)


@router.delete("/me/avatar", response_model=UserProfileOut)
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return accounts.delete_avatar(db, current_user)


@router.get("/avatars/{avatar_id}")
def get_avatar(avatar_id: str, db: Session = Depends(get_db)):
    """Public avatar image. The id is an unguessable random token, and the
    content type comes from the stored magic-byte check, never from the client."""
    blob = accounts.load_avatar(db, avatar_id)
    if blob is None:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return Response(
        content=blob.data,
        media_type=blob.content_type,
        headers={"Cache-Control": "public, max-age=86400, immutable", "X-Content-Type-Options": "nosniff"},
    )


@router.patch("/me", response_model=UserProfileOut)
def update_me(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return accounts.update_profile(db, current_user, payload.model_dump(exclude_unset=True))


@router.post("/google/start", dependencies=[Depends(auth_rate_limit)])
def google_start(payload: GoogleStartRequest, db: Session = Depends(get_db)):
    return google_auth.start(db, payload.state, payload.redirect_uri)


@router.post(
    "/google",
    response_model=GoogleAuthResponse,
    dependencies=[Depends(auth_rate_limit)],
)
def google_auth_endpoint(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    return google_auth.sign_in(db, payload)


@router.post("/username", response_model=TokenResponse)
def set_username(
    payload: SetUsernameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the account username (e.g. after Google signup).

    Tokens remain bound to the immutable user ID after a rename.
    """
    return {"access_token": accounts.change_username(db, current_user, payload.username), "token_type": "bearer"}
