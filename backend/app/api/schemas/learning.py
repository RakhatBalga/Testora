from typing import Literal

from pydantic import BaseModel, field_validator


class DiagnosticStartIn(BaseModel):
    skills: list[Literal["writing", "reading"]]

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, value: list[str]) -> list[str]:
        unique = list(dict.fromkeys(value))
        if not unique:
            raise ValueError("Choose Writing, Reading, or both")
        return unique


class MistakeStatusIn(BaseModel):
    status: Literal["new", "reviewing", "mastered"]


class PlanStatusIn(BaseModel):
    status: Literal["completed", "skipped"]
