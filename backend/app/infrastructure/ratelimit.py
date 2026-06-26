"""Lightweight in-process rate limiting.

A fixed-window counter keyed by client IP + route, used to blunt brute-force and
spam against the auth endpoints. It is per-process: behind multiple workers the
effective limit scales with worker count. For a hard global cap use a shared
store (Redis) or proxy-level limiting — see README operational notes.
"""
import threading
import time
from collections import defaultdict
from ipaddress import ip_address, ip_network

from fastapi import HTTPException, Request, status

from app.infrastructure.config import settings


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


def _is_trusted_proxy(host: str | None) -> bool:
    if not host:
        return False
    try:
        ip = ip_address(host)
    except ValueError:
        return False
    return any(ip in network for network in _trusted_proxy_networks())


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _client_ip(self, request: Request) -> str:
        direct_ip = request.client.host if request.client else "unknown"
        fwd = request.headers.get("x-forwarded-for")
        if fwd and _is_trusted_proxy(direct_ip):
            return fwd.split(",")[0].strip()
        return direct_ip

    async def __call__(self, request: Request) -> None:
        now = time.monotonic()
        key = f"{self._client_ip(request)}:{request.url.path}"
        with self._lock:
            recent = [t for t in self._hits[key] if now - t < self.window]
            if len(recent) >= self.max_requests:
                retry = int(self.window - (now - recent[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please wait and try again.",
                    headers={"Retry-After": str(retry)},
                )
            recent.append(now)
            self._hits[key] = recent


# 10 auth attempts per IP per minute is generous for humans, painful for bots.
auth_rate_limit = RateLimiter(max_requests=10, window_seconds=60)
