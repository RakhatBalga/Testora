from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class WritingTaskOut(BaseModel):
    id: int
    task_type: int
    title: str
    prompt: str
    image_url: Optional[str] = None
    min_words: int
    duration_minutes: int

    class Config:
        from_attributes = True


class WritingSubmitIn(BaseModel):
    task_id: int
    text: str


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
