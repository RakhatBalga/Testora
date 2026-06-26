"""Lightweight in-process rate limiting.

A fixed-window counter keyed by client IP + route, used to blunt brute-force and
spam against the auth endpoints. It is per-process: behind multiple workers the
effective limit scales with worker count. For a hard global cap use a shared
store (Redis) or proxy-level limiting — see README operational notes.
"""
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _client_ip(self, request: Request) -> str:
        # SECURITY ASSUMPTION: the app runs ONLY behind a trusted reverse proxy
        # that overwrites X-Forwarded-For (see docker-compose.prod.yml — backend
        # binds to 127.0.0.1, not the public internet). We take the first hop as
        # the client IP. If the backend were reachable directly, a client could
        # spoof X-Forwarded-For to dodge the per-IP limit — so don't expose it.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

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
