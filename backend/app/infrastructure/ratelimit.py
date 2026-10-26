"""Lightweight in-process rate limiting.

A sliding-window counter keyed by client IP (or user id) + route, used to blunt
brute-force and spam against the auth endpoints and to cap write-heavy ones. It
is per-process: behind multiple workers the effective limit scales with worker
count. For a hard global cap use a shared store (Redis) or proxy-level limiting.

Client IP behind a proxy: the right-most X-Forwarded-For hop that is not one of
our own trusted proxies. The left-most entry is client-controlled and must never
be used for rate limiting.
"""
import logging
import threading
import time
import weakref
from collections import defaultdict
from ipaddress import ip_address, ip_network

from fastapi import HTTPException, Request, status

from app.infrastructure.config import settings

logger = logging.getLogger("testora.ratelimit")

# Sweep expired keys at most this often, so memory stays bounded by the number
# of distinct clients active within one window.
_SWEEP_INTERVAL_SECONDS = 60.0
_MAX_TRACKED_KEYS = 50_000


def _trusted_proxy_networks():
    networks = []
    for raw in settings.TRUSTED_PROXY_CIDRS.split(","):
        value = raw.strip()
        if not value:
            continue
        try:
            networks.append(ip_network(value, strict=False))
        except ValueError:
            continue
    return networks


def _is_trusted_proxy(host: str | None, networks=None) -> bool:
    if not host:
        return False
    try:
        ip = ip_address(host)
    except ValueError:
        return False
    return any(ip in network for network in (networks if networks is not None else _trusted_proxy_networks()))


_first_proxied_request_logged = False


def _log_first_proxied_request(peer: str, forwarded_for: str, resolved: str, trusted: bool) -> None:
    """One-time INFO line so the owner can pick the right TRUSTED_PROXY_CIDRS."""
    global _first_proxied_request_logged
    if _first_proxied_request_logged:
        return
    _first_proxied_request_logged = True
    logger.info(
        "First proxied request: peer=%s X-Forwarded-For=%r peer_is_trusted_proxy=%s resolved_client_ip=%s "
        "TRUSTED_PROXY_CIDRS=%r. Set TRUSTED_PROXY_CIDRS to the range containing the peer (and any other "
        "proxy hops in X-Forwarded-For) so rate limiting sees real client IPs.",
        peer, forwarded_for, trusted, resolved, settings.TRUSTED_PROXY_CIDRS,
    )


def client_ip(request: Request) -> str:
    """Resolve the real client address; never trusts the left-most XFF entry."""
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    networks = _trusted_proxy_networks()
    peer_trusted = _is_trusted_proxy(peer, networks)
    resolved = peer
    if forwarded and peer_trusted:
        # Walk from the proxy side inwards; the first hop that is not ours is
        # the address our outermost trusted proxy saw connecting.
        for hop in reversed([h.strip() for h in forwarded.split(",")]):
            try:
                ip_address(hop)
            except ValueError:
                break  # garbage hop: fall back to the peer rather than guess
            if not _is_trusted_proxy(hop, networks):
                resolved = hop
                break
    if forwarded:
        _log_first_proxied_request(peer, forwarded, resolved, peer_trusted)
    return resolved


_limiters: "weakref.WeakSet[RateLimiter]" = weakref.WeakSet()


def reset_all_limiters() -> None:
    """Forget every counter (used by tests so state never leaks between them)."""
    for limiter in list(_limiters):
        with limiter._lock:
            limiter._hits.clear()


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int, name: str | None = None):
        self.max_requests = max_requests
        self.window = window_seconds
        self.name = name
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()
        _limiters.add(self)

    def _client_ip(self, request: Request) -> str:
        return client_ip(request)

    def _sweep(self, now: float) -> None:
        """Drop keys whose hits all expired (caller holds the lock)."""
        if now - self._last_sweep < _SWEEP_INTERVAL_SECONDS and len(self._hits) < _MAX_TRACKED_KEYS:
            return
        self._last_sweep = now
        for key in [k for k, hits in self._hits.items() if not hits or now - hits[-1] >= self.window]:
            del self._hits[key]

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            recent = [t for t in self._hits[key] if now - t < self.window]
            if len(recent) >= self.max_requests:
                self._hits[key] = recent
                retry = int(self.window - (now - recent[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please wait and try again.",
                    headers={"Retry-After": str(retry)},
                )
            recent.append(now)
            self._hits[key] = recent

    async def __call__(self, request: Request) -> None:
        self.check(f"{self._client_ip(request)}:{request.url.path}")


# 10 auth attempts per IP per minute is generous for humans, painful for bots.
auth_rate_limit = RateLimiter(max_requests=10, window_seconds=60)
