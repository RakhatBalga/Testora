from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.result import AnswerIn, BreakdownItem


Mode = Literal["exam", "practice"]


class ListeningCatalogItem(BaseModel):
    id: int
    title: str
    description: str | None
    duration_minutes: int
    difficulty: str | None
    question_count: int
    content_version: str
    calibration_status: str
    authorship: str


class ListeningQuestionPublic(BaseModel):
    id: int
    order: int
    text: str
    question_type: str
    options: list[str] | None
    word_limit: int | None = None


class ListeningSectionPublic(BaseModel):
    id: int
    order: int
    title: str
    instructions: str | None
    audio_url: str | None
    audio_start: float
    audio_end: float
    map_asset: str | None = None
    questions: list[ListeningQuestionPublic]


class ListeningTestPublic(ListeningCatalogItem):
    schema_version: Literal["testora.listening-public.v1"]
    intro_notice: str
    sections: list[ListeningSectionPublic]


class ListeningProgressIn(BaseModel):
    content_version: str
    mode: Mode
    answers: dict[str, str | list[str] | None] = Field(default_factory=dict)
    current_section: int = Field(0, ge=0, le=3)
    audio_position: float = Field(0, ge=0)
    max_audio_position: float = Field(0, ge=0)


class ListeningProgressOut(ListeningProgressIn):
    status: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListeningSubmitIn(BaseModel):
    content_version: str
    mode: Mode
    submission_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    answers: list[AnswerIn]
    duration_seconds: int | None = Field(None, ge=0, le=10800)


class ListeningSubmitOut(BaseModel):
    schema_version: Literal["testora.listening-submit.v1"]
    attempt_id: int
    test_id: int
    content_version: str
    mode: Mode
    score: int
    total: int
    band: float | None
    accuracy: int
    breakdown: list[BreakdownItem]
    created_at: datetime


class TimestampEvidence(BaseModel):
    segment_id: str | None
    start: float | None
    end: float | None
    quote: str


class ListeningAnswerReview(BaseModel):
    question_id: int
    order: int
    section_order: int
    text: str
    question_type: str
    user_answer: str | None
    correct_answer: str
    is_correct: bool
    explanation: str | None
    target_skill: str | None
    evidence: list[TimestampEvidence]


class TranscriptSegment(BaseModel):
    id: str
    speaker: str
    text: str
    start: float
    end: float


class ListeningSectionReview(BaseModel):
    id: int
    order: int
    title: str
    transcript_segments: list[TranscriptSegment]


class ListeningReviewOut(ListeningSubmitOut):
    schema_version: Literal["testora.listening-review.v1"]
    test_title: str
    duration_seconds: int | None
    sections: list[ListeningSectionReview]
    answers: list[ListeningAnswerReview]
