"""ASGI middleware: request-size limit and request-id logging.

Pure ASGI (not BaseHTTPMiddleware) so the body limit applies before FastAPI
parses anything and streaming responses are not buffered.
"""
import json
import logging
import time
import uuid

from app.infrastructure.config import settings
from app.infrastructure.logging import request_ctx

logger = logging.getLogger("testora.request")

# Multipart framing overhead on top of the file itself.
_UPLOAD_OVERHEAD = 256 * 1024


def body_limit_for(method: str, path: str) -> int:
    """Max request body in bytes for a route (uploads get their own ceiling)."""
    if method == "POST" and path == "/speaking/submit":
        return settings.MAX_AUDIO_UPLOAD_MB * 1024 * 1024 + _UPLOAD_OVERHEAD
    if method == "POST" and path == "/auth/me/avatar":
        return settings.MAX_AVATAR_UPLOAD_MB * 1024 * 1024 + _UPLOAD_OVERHEAD
    return settings.MAX_REQUEST_BODY_BYTES


class BodySizeLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS", "DELETE"):
            await self.app(scope, receive, send)
            return
        limit = body_limit_for(scope["method"], scope["path"])
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None:
            try:
                too_big = int(declared) > limit
            except ValueError:
                too_big = True
            if too_big:
                await self._reject(send, limit)
                return

        received = 0
        responded = False

        async def limited_receive():
            nonlocal received, responded
            message = await receive()
            if message["type"] == "http.request" and not responded:
                received += len(message.get("body", b""))
                if received > limit:
                    # FastAPI turns exceptions raised while reading the body into
                    # a 400, so answer 413 right here and tell the app the client
                    # went away; whatever it tries to send afterwards is dropped.
                    responded = True
                    await self._reject(send, limit)
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message):
            if not responded:
                await send(message)

        await self.app(scope, limited_receive, guarded_send)

    @staticmethod
    async def _reject(send, limit: int):
        body = json.dumps({"detail": f"Request body exceeds the {limit // 1024} KB limit."}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode()),
                                (b"connection", b"close")]})
        await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    """Assigns a request id, echoes it as X-Request-ID and logs one line per request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")[:64]
        rid = incoming if incoming.replace("-", "").isalnum() and incoming else uuid.uuid4().hex[:16]
        scope.setdefault("state", {})["request_id"] = rid  # for error handlers outside this middleware
        ctx_token = request_ctx.set({"rid": rid, "uid": "-"})
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", rid.encode()))
                if not any(name.lower() == b"x-content-type-options" for name, _ in headers):
                    headers.append((b"x-content-type-options", b"nosniff"))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            if scope["path"] not in ("/health", "/health/live"):
                logger.info(
                    "%s %s -> %s in %dms",
                    scope["method"], scope["path"], status_code,
                    (time.perf_counter() - started_at) * 1000,
                )
            request_ctx.reset(ctx_token)
