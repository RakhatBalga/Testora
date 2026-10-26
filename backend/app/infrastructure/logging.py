"""Structured application logging.

Single place that configures the root logger so every module can simply call
`logging.getLogger(__name__)` and get consistent, timestamped, level-tagged
output. Honours the LOG_LEVEL env var (default INFO). Every record carries the
current request id and user id (set by the API middleware / auth dependency).
"""
import logging
import os
from contextvars import ContextVar

# Context holders live here (infrastructure) so the API layer can set them
# without the logging config importing the API.
# A mutable holder, so values set from a threadpool-run dependency (which gets
# a copy of the context) are still visible to the middleware and the handler.
request_ctx: ContextVar[dict] = ContextVar("request_ctx", default={})


def set_user_id(user_id: int) -> None:
    ctx = request_ctx.get()
    if "rid" in ctx:  # only inside a request, never the shared default
        ctx["uid"] = str(user_id)

_CONFIGURED = False


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = request_ctx.get()
        record.request_id = ctx.get("rid", "-")
        record.user_id = ctx.get("uid", "-")
        return True


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] rid=%(request_id)s uid=%(user_id)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(_ContextFilter())
    # Quiet the noisiest third-party loggers a notch so app logs stay readable.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _CONFIGURED = True
