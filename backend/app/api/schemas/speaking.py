from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class SpeakingTaskOut(BaseModel):
    id: int
    part: int
    questions: list[str]
    prep_seconds: int
    speak_seconds: int

    model_config = ConfigDict(from_attributes=True)


class SpeakingSubmissionOut(BaseModel):
    id: int
    task_id: int
    task_part: int
    questions: list[str]
    audio_url: str
    transcript: Optional[str] = None
    band: Optional[float] = None
    feedback: Optional[Any] = None
    created_at: datetime


class SpeakingSubmissionSummary(BaseModel):
    id: int
    task_id: int
    task_part: int
    audio_url: str
    band: Optional[float] = None
    created_at: datetime
