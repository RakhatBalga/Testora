from typing import List, Optional
from pydantic import BaseModel


class QuestionOut(BaseModel):
    id: int
    text: str
    options: List[str]
    order: int

    class Config:
        from_attributes = True


class TestOut(BaseModel):
    id: int
    title: str
    test_type: str
    description: Optional[str] = None
    duration_minutes: int

    class Config:
        from_attributes = True


class TestDetail(TestOut):
    audio_url: Optional[str] = None
    content: Optional[str] = None
    questions: List[QuestionOut]
