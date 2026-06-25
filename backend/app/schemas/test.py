from typing import List, Optional
from pydantic import BaseModel


class EvidenceSpan(BaseModel):
    paragraph: int
    text: str

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id: int
    text: str
    question_type: str
    options: Optional[List[str]] = None  # null for free-text questions
    order: int
    evidence: Optional[List[EvidenceSpan]] = None

    class Config:
        from_attributes = True


class SectionOut(BaseModel):
    id: int
    order: int
    title: str
    instructions: Optional[str] = None
    passage: Optional[str] = None
    audio_url: Optional[str] = None
    questions: List[QuestionOut]

    class Config:
        from_attributes = True


class TestOut(BaseModel):
    id: int
    title: str
    test_type: str
    description: Optional[str] = None
    duration_minutes: int
    difficulty: Optional[str] = None
    question_count: int = 0

    class Config:
        from_attributes = True


class TestDetail(TestOut):
    sections: List[SectionOut]
