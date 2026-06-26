from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel


class AnswerIn(BaseModel):
    question_id: int
    answer: Optional[Union[str, List[str]]] = None
    marked_for_review: bool = False


class SubmitIn(BaseModel):
    test_id: int
    answers: List[AnswerIn]
    duration_seconds: Optional[int] = None


class AnswerResult(BaseModel):
    question_id: int
    text: str
    question_type: str
    user_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool
    marked_for_review: bool = False
    explanation: Optional[str] = None


class BreakdownItem(BaseModel):
    question_type: str
    label: str
    correct: int
    total: int
    accuracy: int


class AttemptResult(BaseModel):
    id: int
    test_id: int
    test_title: str
    test_type: str
    score: int
    total: int
    band: Optional[float] = None
    correct: int
    incorrect: int
    accuracy: int
    duration_seconds: Optional[int] = None
    breakdown: List[BreakdownItem] = []
    created_at: datetime
    answers: List[AnswerResult]


class AttemptSummary(BaseModel):
    id: int
    test_id: int
    test_title: str
    test_type: str
    score: int
    total: int
    band: Optional[float] = None
    created_at: datetime
