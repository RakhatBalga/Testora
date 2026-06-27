from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_half_band(value: float) -> float:
    if abs((value * 2) - round(value * 2)) > 1e-9:
        raise ValueError("target_band must be a whole or half IELTS band")
    return round(value, 1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    # Max 72 bytes is bcrypt's hard limit — anything beyond is silently ignored,
    # so we cap here to avoid a misleading "long" password.
    password: str = Field(..., min_length=8, max_length=72)
    target_band: float = Field(7.5, ge=5.0, le=9.0)

    _target_band_step = field_validator("target_band")(_validate_half_band)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfileOut(BaseModel):
    username: str
    target_band: float
    current_level: float | None = None
    current_level_source: str | None = None
    exam_date: date | None = None
    weekly_study_days: int = 3
    daily_study_minutes: int = 30
    primary_focus: str = "balanced"
    onboarding_completed: bool = False


class UserProfileUpdate(BaseModel):
    target_band: float | None = Field(None, ge=5.0, le=9.0)
    current_level: float | None = Field(None, ge=4.0, le=8.5)
    exam_date: date | None = None
    weekly_study_days: int | None = Field(None, ge=1, le=7)
    daily_study_minutes: Literal[15, 30, 45, 60, 90] | None = None
    primary_focus: Literal["writing", "reading", "speaking", "balanced"] | None = None
    onboarding_completed: bool | None = None

    @field_validator("target_band", "current_level")
    @classmethod
    def validate_band_step(cls, value: float | None) -> float | None:
        return None if value is None else _validate_half_band(value)

    @field_validator("exam_date")
    @classmethod
    def validate_exam_date(cls, value: date | None) -> date | None:
        if value is not None and value <= date.today():
            raise ValueError("exam_date must be in the future")
        return value

    @model_validator(mode="after")
    def validate_target_above_current(self):
        if self.target_band is not None and self.current_level is not None and self.target_band < self.current_level:
            raise ValueError("target_band must be greater than or equal to current_level")
        return self
