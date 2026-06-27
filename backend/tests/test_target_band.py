import pytest
from datetime import date, timedelta
from pydantic import ValidationError

from app.api.routers.analytics import _target_for
from app.api.schemas.auth import RegisterRequest, UserProfileUpdate
from app.application.analytics.band_gap import DEFAULT_TARGET
from app.domain.models.user import User


def test_register_accepts_half_band_target():
    payload = RegisterRequest(username="student", password="strong-password", target_band=7.5)

    assert payload.target_band == 7.5


@pytest.mark.parametrize("value", [6.25, 7.75])
def test_target_band_rejects_non_half_steps(value):
    with pytest.raises(ValidationError):
        UserProfileUpdate(target_band=value)


def test_analytics_target_uses_user_profile_when_query_is_absent():
    user = User(username="student", password="hash", target_band=6.5)

    assert _target_for(user, None) == 6.5


def test_analytics_target_prefers_explicit_query_value():
    user = User(username="student", password="hash", target_band=6.5)

    assert _target_for(user, 8.0) == 8.0


def test_analytics_target_falls_back_for_legacy_user_without_value():
    user = User(username="student", password="hash")
    user.target_band = None

    assert _target_for(user, None) == DEFAULT_TARGET


def test_profile_rejects_target_below_current_level():
    with pytest.raises(ValidationError, match="greater than or equal"):
        UserProfileUpdate(target_band=6.5, current_level=7.0)


def test_profile_rejects_past_exam_date():
    with pytest.raises(ValidationError, match="future"):
        UserProfileUpdate(exam_date=date.today() - timedelta(days=1))


def test_profile_accepts_not_sure_current_level():
    payload = UserProfileUpdate(target_band=7.5, current_level=None)

    assert payload.current_level is None
