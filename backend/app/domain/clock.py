"""The clock used for stored timestamps."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC "now" matching how timestamps are stored (replaces utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
