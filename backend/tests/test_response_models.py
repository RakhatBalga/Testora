"""Typed responses for the thin routers must not change or break their payloads."""

import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/analytics/weaknesses",
        "/analytics/blockers",
        "/analytics/band-gap",
        "/analytics/band-trajectory",
        "/analytics/weekly-weakest",
        "/analytics/streak",
        "/analytics/blocker-history",
        "/analytics/daily-plan",
        "/analytics/recommendations",
        "/analytics/recurring-mistakes",
        "/history",
        "/learning/dashboard",
        "/learning/diagnostic",
        "/learning/study-plan",
        "/learning/mistakes",
        "/vocabulary/words",
    ],
)
def test_empty_account_endpoints_respond(api, path):
    response = api.client.get(path, headers=api.headers)
    assert response.status_code == 200, response.text


def test_band_gap_shape_is_stable_for_new_users(api):
    body = api.client.get("/analytics/band-gap", headers=api.headers).json()
    assert body == {
        "current": None,
        "target": 7.5,
        "gap": None,
        "per_skill": {},
        "lowest_skill": None,
        "has_data": False,
    }


def test_openapi_documents_analytics_responses(api):
    from app.main import app

    schema = app.openapi()
    ref = schema["paths"]["/analytics/streak"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ref["$ref"].endswith("StreakOut")
