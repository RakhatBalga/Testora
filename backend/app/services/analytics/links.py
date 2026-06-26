"""Frontend route helpers for analytics-generated actions."""

_PRACTICE_HREFS = {
    "writing": "/writing",
    "speaking": "/speaking",
    "reading": "/tests/reading",
    "listening": "/tests/listening",
}


def practice_href(skill: str | None) -> str:
    if not skill:
        return "/practice"
    return _PRACTICE_HREFS.get(skill.lower(), "/practice")
