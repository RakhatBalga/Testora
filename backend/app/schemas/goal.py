from datetime import date

from pydantic import BaseModel, Field


class GoalRequest(BaseModel):
    target_band: float = Field(ge=4.0, le=9.0)
    current_band: float | None = Field(default=None, ge=4.0, le=9.0)
    exam_date: date | None = None


class GoalResponse(BaseModel):
    target_band: float
    current_band: float | None = None
    exam_date: date | None = None

    class Config:
        from_attributes = True
