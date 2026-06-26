from types import SimpleNamespace

from app.infrastructure.config import settings
from app.infrastructure.ratelimit import RateLimiter


def _request(peer: str, forwarded_for: str | None = None):
    headers = {}
    if forwarded_for:
        headers["x-forwarded-for"] = forwarded_for
    return SimpleNamespace(
        client=SimpleNamespace(host=peer),
        headers=headers,
        url=SimpleNamespace(path="/auth/login"),
    )


def test_x_forwarded_for_is_ignored_from_untrusted_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "127.0.0.1/32")
    limiter = RateLimiter(max_requests=10, window_seconds=60)

    assert limiter._client_ip(_request("203.0.113.10", "198.51.100.7")) == "203.0.113.10"


def test_x_forwarded_for_is_used_from_trusted_proxy(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "127.0.0.1/32,172.16.0.0/12")
    limiter = RateLimiter(max_requests=10, window_seconds=60)

    assert limiter._client_ip(_request("172.18.0.1", "198.51.100.7")) == "198.51.100.7"
