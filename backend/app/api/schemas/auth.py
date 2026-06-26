from pydantic import BaseModel, Field, field_validator


def _validate_half_band(value: float) -> float:
    if abs((value * 2) - round(value * 2)) > 1e-9:
        raise ValueError("target_band must be a whole or half IELTS band")
    return round(value, 1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    # Max 72 bytes is bcrypt's hard limit — anything beyond is silently ignored,
    # so we cap here to avoid a misleading "long" password.
    password: str = Field(..., min_length=8, max_length=72)
    target_band: float = Field(7.5, ge=4.0, le=9.0)

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


class UserProfileUpdate(BaseModel):
    target_band: float = Field(..., ge=4.0, le=9.0)

    _target_band_step = field_validator("target_band")(_validate_half_band)
