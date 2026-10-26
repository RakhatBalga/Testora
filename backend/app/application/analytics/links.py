"""Frontend route helpers for analytics-generated actions."""

from app.application import frontend_routes as routes

_PRACTICE_HREFS = {skill: routes.library(skill) for skill in routes.SKILLS}


def practice_href(skill: str | None) -> str:
    if not skill:
        return routes.practice()
    return _PRACTICE_HREFS.get(skill.lower(), routes.practice())
