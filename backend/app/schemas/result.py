from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class AnswerIn(BaseModel):
    question_id: int
    answer: Optional[str] = None


class SubmitIn(BaseModel):
    test_id: int
    answers: List[AnswerIn]


class AnswerResult(BaseModel):
    question_id: int
    text: str
    user_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool


class AttemptResult(BaseModel):
    id: int
    test_id: int
    test_title: str
    score: int
    total: int
    created_at: datetime
    answers: List[AnswerResult]


class AttemptSummary(BaseModel):
    id: int
    test_id: int
    test_title: str
    score: int
    total: int
    created_at: datetime
