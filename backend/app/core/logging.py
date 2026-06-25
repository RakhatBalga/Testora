"""Structured application logging.

Single place that configures the root logger so every module can simply call
`logging.getLogger(__name__)` and get consistent, timestamped, level-tagged
output. Honours the LOG_LEVEL env var (default INFO).
"""
import logging
import os

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    # Quiet the noisiest third-party loggers a notch so app logs stay readable.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _CONFIGURED = True
