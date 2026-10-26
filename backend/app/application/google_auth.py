"""Google sign-in: exchange the authorization code and find or create the user."""
import secrets

import bcrypt
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.application.oauth import consume_flow, start_flow
from app.domain.models.user import User
from app.infrastructure.config import settings
from app.infrastructure.security import create_access_token

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _require_configured() -> None:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google auth is not configured")


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


def start(db: Session, state: str, redirect_uri: str) -> dict:
    _require_configured()
    return {"authorization_url": start_flow(db, state, redirect_uri)}


def sign_in(db: Session, payload) -> dict:
    _require_configured()
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

        dummy_password = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode("utf-8")
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

    return {
        "access_token": create_access_token(user.id, user.token_version or 0),
        "token_type": "bearer",
        "is_new_user": is_new_user,
        "username": user.username,
    }
