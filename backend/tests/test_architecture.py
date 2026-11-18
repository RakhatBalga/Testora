"""The layering rules of the backend, enforced: api -> application -> domain,
with infrastructure at the edge."""

import ast
import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler

from app.api.errors import application_error_handler
from app.application import errors

APP = Path(__file__).resolve().parents[1] / "app"


def _imports(layer: str) -> list[tuple[str, str]]:
    """(file, imported module) for every import statement in a layer."""
    found = []
    for path in sorted((APP / layer).rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                found.extend((str(path.relative_to(APP)), alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.append((str(path.relative_to(APP)), node.module))
    return found


def _violations(layer: str, forbidden: tuple[str, ...]) -> list[tuple[str, str]]:
    return [
        (path, module)
        for path, module in _imports(layer)
        if any(module == name or module.startswith(name + ".") for name in forbidden)
    ]


def test_domain_depends_on_nothing_above_it():
    assert _violations("domain", ("fastapi", "starlette", "app.infrastructure", "app.api", "app.application")) == []


def test_application_does_not_know_the_web_framework_or_the_api_layer():
    assert _violations("application", ("fastapi", "starlette", "app.api")) == []


def test_application_reaches_ai_providers_only_through_its_ports():
    assert _violations("application", ("app.infrastructure.ai",)) == []


def test_api_layer_does_not_run_orm_queries():
    offenders = [
        f"{path.relative_to(APP)}:{number}"
        for path in sorted((APP / "api").rglob("*.py"))
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if any(call in line for call in ("db.query(", "db.get(", "db.add(", "db.commit(", "db.execute("))
    ]
    assert offenders == []


_ERRORS = [cls for cls in vars(errors).values() if isinstance(cls, type) and issubclass(cls, errors.ApplicationError)]


@pytest.mark.parametrize("error", _ERRORS, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize(
    "detail,headers",
    [
        ("Submission not found", None),
        ({"code": "ai_daily_limit", "message": "Daily AI limit reached.", "resets_at": "x"}, {"Retry-After": "30"}),
    ],
)
def test_application_errors_answer_exactly_like_http_exceptions(error, detail, headers):
    ours = asyncio.run(application_error_handler(None, error(detail, headers=headers)))
    theirs = asyncio.run(http_exception_handler(None, HTTPException(error.status_code, detail, headers=headers)))

    assert ours.status_code == theirs.status_code == error.status_code
    assert ours.body == theirs.body
    assert ours.raw_headers == theirs.raw_headers


def test_application_error_reaches_the_client_as_before(api):
    missing = api.client.get("/writing/submissions/999", headers=api.headers)
    assert missing.status_code == 404 and missing.json() == {"detail": "Submission not found"}

    taken = api.client.post("/auth/register", json={"username": "student", "password": "long-enough-password"})
    assert taken.status_code == 400 and taken.json() == {"detail": "Username already taken"}
