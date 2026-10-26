from datetime import datetime
from typing import Annotated, List, Optional, Union
from pydantic import BaseModel, Field

# Generous ceilings: a real answer is a word or a short phrase; a real test has
# at most ~40 questions. They only exist to keep stored JSON/rows bounded.
MAX_ANSWER_CHARS = 500
MAX_ANSWER_ITEMS = 10
MAX_ANSWERS_PER_SUBMIT = 200

AnswerText = Field(max_length=MAX_ANSWER_CHARS)


class AnswerIn(BaseModel):
    question_id: int
    answer: Optional[
        Union[
            Annotated[str, AnswerText], Annotated[List[Annotated[str, AnswerText]], Field(max_length=MAX_ANSWER_ITEMS)]
        ]
    ] = None
    marked_for_review: bool = False


class SubmitIn(BaseModel):
    test_id: int
    answers: List[AnswerIn] = Field(max_length=MAX_ANSWERS_PER_SUBMIT)
    duration_seconds: Optional[int] = Field(None, ge=0, le=10800)
    # Optional client-generated key; a repeated key returns the first attempt.
    submission_key: Optional[str] = Field(None, min_length=8, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")


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
