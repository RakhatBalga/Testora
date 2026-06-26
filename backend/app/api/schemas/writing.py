from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.config import settings


class WritingTaskOut(BaseModel):
    id: int
    task_type: int
    title: str
    prompt: str
    image_url: Optional[str] = None
    min_words: int
    duration_minutes: int

    model_config = ConfigDict(from_attributes=True)


class WritingSubmitIn(BaseModel):
    task_id: int
    # Bounded to protect memory, AI token cost, and against abuse. A real essay
    # is well under this ceiling; an empty submission is rejected.
    text: str = Field(..., min_length=1, max_length=settings.MAX_WRITING_CHARS)


class WritingSubmissionOut(BaseModel):
    id: int
    task_id: int
    task_title: str
    task_prompt: str
    text: str
    word_count: int
    status: str
    band: Optional[float] = None
    feedback: Optional[Any] = None
    created_at: datetime


class WritingSubmissionSummary(BaseModel):
    id: int
    task_id: int
    task_title: str
    word_count: int
    status: str
    band: Optional[float] = None
    created_at: datetime
