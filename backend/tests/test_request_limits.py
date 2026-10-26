"""Rate-limit client IP parsing, limiter pruning, request body cap, input bounds."""
import logging
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas.listening import ListeningProgressIn
from app.api.schemas.result import AnswerIn, SubmitIn
from app.infrastructure import ratelimit
from app.infrastructure.config import settings
from app.infrastructure.ratelimit import RateLimiter, client_ip
from app.main import app


def _request(peer, forwarded_for=None):
    headers = {"x-forwarded-for": forwarded_for} if forwarded_for else {}
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers,
                           url=SimpleNamespace(path="/auth/login"))


@pytest.fixture(autouse=True)
def _reset_log_flag(monkeypatch):
    monkeypatch.setattr(ratelimit, "_first_proxied_request_logged", False)


def test_rightmost_untrusted_hop_is_the_client(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    # The client forged the left-most entries; the proxy appended the real address.
    request = _request("10.1.2.3", "6.6.6.6, 203.0.113.9")
    assert client_ip(request) == "203.0.113.9"


def test_trusted_proxy_chain_is_skipped(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8,172.16.0.0/12")
    assert client_ip(_request("10.0.0.1", "198.51.100.7, 172.16.5.5, 10.9.9.9")) == "198.51.100.7"


def test_forged_xff_from_untrusted_peer_is_ignored(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    assert client_ip(_request("203.0.113.50", "1.2.3.4")) == "203.0.113.50"


def test_garbage_hop_falls_back_to_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    assert client_ip(_request("10.0.0.1", "1.2.3.4, not-an-ip")) == "10.0.0.1"


def test_first_proxied_request_is_logged_once(monkeypatch, caplog):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "")
    with caplog.at_level(logging.INFO, logger="testora.ratelimit"):
        client_ip(_request("10.1.1.1", "203.0.113.9"))
        client_ip(_request("10.1.1.1", "203.0.113.9"))
    lines = [r for r in caplog.records if "First proxied request" in r.getMessage()]
    assert len(lines) == 1
    assert "peer=10.1.1.1" in lines[0].getMessage()


def test_limiter_blocks_then_prunes_expired_keys(monkeypatch):
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.check("a")
    limiter.check("a")
    with pytest.raises(HTTPException) as error:
        limiter.check("a")
    assert error.value.status_code == 429 and int(error.value.headers["Retry-After"]) >= 1
    for index in range(100):
        limiter.check(f"client-{index}")
    # Jump past the window: the next sweep drops every expired key.
    real = ratelimit.time.monotonic
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: real() + 3600)
    limiter.check("fresh")
    assert list(limiter._hits) == ["fresh"]


def test_oversized_body_is_rejected_before_parsing(monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BODY_BYTES", 1000)
    client = TestClient(app)
    response = client.post("/auth/login", content=b"x" * 5000, headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert response.headers["x-request-id"]


def test_streamed_body_without_content_length_is_capped(monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BODY_BYTES", 1000)

    def chunks():
        for _ in range(20):
            yield b"y" * 200

    response = TestClient(app).post("/auth/login", content=chunks(), headers={"content-type": "application/json"})
    assert response.status_code == 413


def test_upload_routes_get_a_larger_cap():
    from app.api.middleware import body_limit_for

    assert body_limit_for("POST", "/speaking/submit") > settings.MAX_AUDIO_UPLOAD_MB * 1024 * 1024
    assert body_limit_for("POST", "/auth/me/avatar") > settings.MAX_AVATAR_UPLOAD_MB * 1024 * 1024
    assert body_limit_for("POST", "/results/submit") == settings.MAX_REQUEST_BODY_BYTES


def test_unbounded_fields_now_have_limits():
    with pytest.raises(ValidationError):
        AnswerIn(question_id=1, answer="x" * 501)
    with pytest.raises(ValidationError):
        AnswerIn(question_id=1, answer=["a"] * 11)
    with pytest.raises(ValidationError):
        SubmitIn(test_id=1, answers=[AnswerIn(question_id=i) for i in range(201)])
    with pytest.raises(ValidationError):
        ListeningProgressIn(content_version="v1", mode="exam", answers={str(i): "a" for i in range(201)})
    with pytest.raises(ValidationError):
        ListeningProgressIn(content_version="v1", mode="exam", answers={"1": "z" * 501})
    ok = ListeningProgressIn(content_version="v1", mode="exam", answers={"1": ["a", "b"], "2": None})
    assert ok.answers["1"] == ["a", "b"]
