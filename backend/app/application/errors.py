"""Errors the use cases raise. They carry no web framework types.

Each class names one kind of failure; `status_code` is the HTTP status the API
adapter answers with (`app/api/errors.py` is the only place that builds the
response). `detail` is the client-facing message or structured payload and
`headers` optional response metadata such as Retry-After.
"""

from typing import Any


class ApplicationError(Exception):
    status_code = 500

    def __init__(self, detail: Any = None, headers: dict[str, str] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.headers = headers


class InvalidRequest(ApplicationError):
    status_code = 400


class AuthenticationFailed(ApplicationError):
    status_code = 401


class Forbidden(ApplicationError):
    status_code = 403


class NotFound(ApplicationError):
    status_code = 404


class Conflict(ApplicationError):
    status_code = 409


class UnsupportedMedia(ApplicationError):
    status_code = 415


class ValidationFailed(ApplicationError):
    status_code = 422


class TooManyRequests(ApplicationError):
    status_code = 429


class NotConfigured(ApplicationError):
    status_code = 501


class UpstreamInvalidResponse(ApplicationError):
    status_code = 502


class ServiceUnavailable(ApplicationError):
    status_code = 503


class UpstreamTimeout(ApplicationError):
    status_code = 504
