"""Timezone-aware day-boundary helpers.

Submission timestamps are stored as naive UTC. Streaks and "today's plan" are
about the *user's* day, so they must be computed in the configured local
timezone (APP_TIMEZONE) — otherwise day boundaries shift by several hours for
CIS/MENA users and streaks break around local midnight.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.infrastructure.config import settings


def app_tz() -> ZoneInfo | timezone:
    try:
        return ZoneInfo(settings.APP_TIMEZONE)
    except Exception:  # noqa: BLE001 — bad tz name shouldn't crash requests
        return timezone.utc


def to_local_date(dt: datetime) -> date:
    """Convert a stored (naive UTC) or aware datetime to a local calendar date."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(app_tz()).date()


def local_today() -> date:
    return datetime.now(app_tz()).date()
