"""Optional production error tracking.

A thin, dependency-light hook: if SENTRY_DSN is configured AND sentry-sdk is
installed, initialise it so unhandled exceptions are reported. If either is
missing it is a silent no-op — local/dev runs need no Sentry, and the app never
hard-depends on it. Install with `pip install sentry-sdk` to enable.
"""
import logging

from app.core.config import settings

logger = logging.getLogger("testora")


def init_error_tracking() -> None:
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk  # type: ignore
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; skipping.")
        return
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        # Conservative trace sampling; tune per traffic.
        traces_sample_rate=0.1,
    )
    logger.info("Error tracking enabled (Sentry, env=%s)", settings.APP_ENV)
