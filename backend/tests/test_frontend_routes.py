"""Links the API sends to the frontend must point at real frontend pages."""

import json
import re
from pathlib import Path

import pytest

from app.application import frontend_routes as routes

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = json.loads((ROOT / "frontend/src/shared/config/routes.json").read_text())["patterns"]


def _is_known_page(href: str) -> bool:
    parts = href.split("?")[0].strip("/").split("/")
    for pattern in PATTERNS:
        pp = pattern.strip("/").split("/")
        if len(pp) == len(parts) and all(p == "{id}" or p == q for p, q in zip(pp, parts)):
            return True
    return False


def _all_hrefs() -> list[str]:
    hrefs = [
        routes.practice(),
        routes.mistakes(),
        routes.mistakes("writing"),
        routes.writing_library(),
        routes.writing_library(2),
    ]
    for skill in routes.SKILLS:
        hrefs += [routes.library(skill), routes.exam(skill, 7), routes.result(skill, 7)]
    return hrefs


@pytest.mark.parametrize("href", _all_hrefs())
def test_every_builder_points_at_a_frontend_page(href):
    assert _is_known_page(href), f"{href} is not a page listed in frontend routes.json"


def test_old_urls_are_gone():
    assert not any(h.startswith(("/tests/", "/result/")) for h in _all_hrefs())


GENERATOR_FILES = [
    "analytics/links.py",
    "analytics/band_gap.py",
    "analytics/daily_plan.py",
    "analytics/recommendations.py",
    "history/history.py",
    "learning/dashboard.py",
    "learning/notebook.py",
    "learning/study_plan.py",
]


@pytest.mark.parametrize("name", GENERATOR_FILES)
def test_generators_do_not_hardcode_frontend_paths(name):
    source = (ROOT / "backend/app/application" / name).read_text()
    literal = re.compile(r"""f?["']/(reading|listening|writing|speaking|mistakes|practice|result|tests)\b""")
    assert not literal.search(source), f"{name} builds a frontend path by hand; use frontend_routes"
