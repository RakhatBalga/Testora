"""Single place where the backend builds URLs of frontend pages.

Mirrors ``frontend/src/shared/config/routes.ts``; both are checked against
``frontend/src/shared/config/routes.json`` by tests, so a renamed page cannot
leave stale links in API responses.

Scheme, identical for every skill:
  library  /<skill>
  exam     /<skill>/<id>
  result   /<skill>/result/<id>
"""

from __future__ import annotations

SKILLS = ("reading", "listening", "writing", "speaking")


def library(skill: str) -> str:
    return f"/{skill}"


def exam(skill: str, item_id: int) -> str:
    return f"/{skill}/{item_id}"


def result(skill: str, item_id: int) -> str:
    return f"/{skill}/result/{item_id}"


def writing_library(task_type: int | None = None) -> str:
    return f"/writing?task={task_type}" if task_type else "/writing"


def practice() -> str:
    return "/practice"


def mistakes(skill: str | None = None) -> str:
    return f"/mistakes?skill={skill}" if skill else "/mistakes"
