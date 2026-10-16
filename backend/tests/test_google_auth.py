import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routers import auth
from app.api.schemas.auth import GoogleAuthRequest, GoogleStartRequest
from app.application.oauth import consume_flow
from app.domain.models.oauth import OAuthFlow
from app.domain.models.user import User
from app.infrastructure.config import settings
from app.infrastructure.database import Base
from app.infrastructure.security import access_token_user_id

REDIRECT = "http://localhost:3000/auth/google/callback"


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setattr(settings, "CORS_ORIGINS", "http://localhost:3000")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def start(db):
    state = secrets.token_urlsafe(32)
    result = auth.google_start(GoogleStartRequest(state=state, redirect_uri=REDIRECT), db)
    return state, parse_qs(urlparse(result["authorization_url"]).query)


def test_pkce_and_single_use(db):
    state, params = start(db)
    assert params["state"] == [state]
    assert params["code_challenge_method"] == ["S256"]
    verifier = consume_flow(db, state, REDIRECT)
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert params["code_challenge"] == [expected]
    with pytest.raises(HTTPException):
        consume_flow(db, state, REDIRECT)


@pytest.mark.parametrize("redirect", ["https://evil.test/auth/google/callback", REDIRECT + "?next=evil", REDIRECT + "/", "http://localhost:3000.evil.test/auth/google/callback"])
def test_redirect_must_exactly_match_configured_callback(db, redirect):
    with pytest.raises(HTTPException) as error:
        auth.google_start(GoogleStartRequest(state=secrets.token_urlsafe(32), redirect_uri=redirect), db)
    assert error.value.status_code == 400
    assert db.query(OAuthFlow).count() == 0


def test_missing_and_expired_state_rejected_before_google(db, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid state must not call Google")
    monkeypatch.setattr(auth.httpx, "Client", unexpected)
    state, _ = start(db)
    db.query(OAuthFlow).update({OAuthFlow.expires_at: datetime.utcnow() - timedelta(seconds=1)})
    db.commit()
    for value in (state, secrets.token_urlsafe(32)):
        with pytest.raises(HTTPException) as error:
            auth.google_auth(GoogleAuthRequest(code="code", state=value, redirect_uri=REDIRECT), db)
        assert error.value.status_code == 400


@pytest.mark.parametrize("verified", [True, False, None, "true"])
def test_exchange_sends_pkce_and_only_trusts_verified_email(db, monkeypatch, verified):
    state, params = start(db)
    requests = []
    def handler(request):
        requests.append(request)
        if request.url == auth.GOOGLE_TOKEN_URL:
            data = parse_qs(request.content.decode())
            verifier = data["code_verifier"][0]
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            assert params["code_challenge"] == [challenge]
            assert data["redirect_uri"] == [REDIRECT]
            return httpx.Response(200, json={"access_token": "google-token"})
        return httpx.Response(200, json={"id": "google-user", "email": "student@example.com", "verified_email": verified})
    client_type = httpx.Client
    monkeypatch.setattr(auth.httpx, "Client", lambda **kw: client_type(transport=httpx.MockTransport(handler)))
    payload = GoogleAuthRequest(code="code", state=state, redirect_uri=REDIRECT)
    if verified is True:
        result = auth.google_auth(payload, db)
        assert access_token_user_id(result["access_token"]) == db.query(User).one().id
    else:
        with pytest.raises(HTTPException) as error:
            auth.google_auth(payload, db)
        assert error.value.status_code == 401
        assert db.query(User).count() == 0
    assert len(requests) == 2
    with pytest.raises(HTTPException):
        auth.google_auth(payload, db)
    assert len(requests) == 2
