import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models.oauth import OAuthFlow
from app.infrastructure.config import settings


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _state_hash(state: str) -> str:
    return hashlib.sha256(state.encode("ascii")).hexdigest()


def validate_redirect(redirect_uri: str) -> None:
    origins = {settings.FRONTEND_URL.rstrip("/"), *settings.cors_origins_list}
    allowed = {origin.rstrip("/") + "/auth/google/callback" for origin in origins}
    if redirect_uri not in allowed:
        raise HTTPException(400, "Invalid Google redirect URI")


def start_flow(db: Session, state: str, redirect_uri: str) -> str:
    validate_redirect(redirect_uri)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    db.query(OAuthFlow).filter(OAuthFlow.expires_at < _now()).delete()
    db.add(
        OAuthFlow(
            state_hash=_state_hash(state),
            verifier=verifier,
            redirect_uri=redirect_uri,
            expires_at=_now() + timedelta(minutes=10),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Authorization flow already exists; start again")
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "prompt": "select_account",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )


def consume_flow(db: Session, state: str, redirect_uri: str) -> str:
    validate_redirect(redirect_uri)
    key = _state_hash(state)
    changed = (
        db.query(OAuthFlow)
        .filter(
            OAuthFlow.state_hash == key,
            OAuthFlow.redirect_uri == redirect_uri,
            OAuthFlow.consumed.is_(False),
            OAuthFlow.expires_at > _now(),
        )
        .update({OAuthFlow.consumed: True}, synchronize_session=False)
    )
    if changed != 1:
        db.rollback()
        raise HTTPException(400, "Invalid or expired Google authorization flow; start again")
    verifier = db.get(OAuthFlow, key).verifier
    # Commit before the network call: concurrent exchanges cannot reuse a flow.
    db.commit()
    return verifier
