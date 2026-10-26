"""Retry policy shared by every AI transport.

* transient (timeouts, connection errors, HTTP 408/5xx, 429) -> retry with
  exponential backoff; a 429/503 Retry-After is respected up to a ceiling;
* permanent (other 4xx: bad request, bad key, forbidden, not found) -> never
  retried, it would only waste the user's time and a grading slot;
* schema / JSON validation failure after a successful call -> re-asked once
  by the engine (`engine.py`), not here.
"""

from __future__ import annotations

import email.utils
import time
from dataclasses import dataclass

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
# Never sleep longer than this for one retry; a longer Retry-After gives up so
# the grading slot is released and the user gets a clean "try again" result.
MAX_RETRY_AFTER_SECONDS = 30.0


class TransientError(Exception):
    """Worth retrying: the same request may succeed shortly."""

    def __init__(self, message: str, *, status: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class PermanentError(Exception):
    """Not worth retrying (bad request, auth, forbidden, unsupported)."""

    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


class SchemaError(ValueError):
    """The call succeeded but the output was not valid JSON for the schema."""


class TruncatedResponse(Exception):
    """The model hit the output-token cap; output is unusable. Not retried."""


def is_transient_status(status: int) -> bool:
    return status == 408 or status == 429 or status >= 500


def parse_retry_after(value: str | None) -> float | None:
    """Retry-After as seconds (either delta-seconds or an HTTP date)."""
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    return max(0.0, when.timestamp() - time.time())


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = MAX_ATTEMPTS
    backoff_base: float = BACKOFF_BASE_SECONDS
    max_retry_after: float = MAX_RETRY_AFTER_SECONDS

    def delay(self, attempt: int, retry_after: float | None = None) -> float | None:
        """Seconds to wait before attempt `attempt + 1`, or None to give up."""
        if attempt >= self.max_attempts:
            return None
        backoff = self.backoff_base * (2 ** (attempt - 1))
        if retry_after is not None:
            if retry_after > self.max_retry_after:
                return None
            return max(backoff, retry_after)
        return backoff


DEFAULT_POLICY = RetryPolicy()
