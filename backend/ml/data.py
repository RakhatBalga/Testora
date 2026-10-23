"""Versioned, pseudonymous research records. Raw data stays outside Git."""
import json
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SpeakingSample(Record):
    schema_version: Literal["speaking.v1"] = "speaking.v1"
    sample_id: str = Field(min_length=1)
    speaker_id: str = Field(min_length=1)
    audio_path: str = Field(min_length=1)
    reference_text: str = Field(min_length=1)
    expert_band: float = Field(ge=0, le=9, multiple_of=0.5)
    # An independently produced transcript-only LLM score, not a target feature.
    llm_band: float | None = Field(default=None, ge=0, le=9)
    consent: Literal[True]

    @field_validator("sample_id", "speaker_id", "audio_path", "reference_text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class ResponseRecord(Record):
    schema_version: Literal["response.v1"] = "response.v1"
    response_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    content_version: str = Field(min_length=1)
    skill: Literal["reading", "listening"]
    question_type: str = Field(min_length=1)
    correct: bool = Field(strict=True)
    answered_at: datetime

    @field_validator("response_id", "learner_id", "item_id", "content_version", "question_type")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("answered_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("answered_at requires an explicit timezone")
        return value

    @property
    def item_key(self) -> str:
        # JSON tuple avoids ambiguous separator collisions.
        return json.dumps([self.skill, self.content_version, self.item_id])

    @property
    def skill_key(self) -> str:
        return json.dumps([self.skill, self.question_type])


T = TypeVar("T", bound=Record)


def read_jsonl(path: Path, model: type[T]) -> list[T]:
    records = []
    seen = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = model.model_validate_json(line)
            key = getattr(record, "sample_id", getattr(record, "response_id", None))
            if key in seen:
                raise ValueError("duplicate record ID")
            seen.add(key)
            records.append(record)
        except ValueError as exc:
            # Do not echo transcripts or other raw personal data in errors.
            raise ValueError(f"Invalid {model.__name__} at line {number}") from None
    if not records:
        raise ValueError("Dataset is empty")
    return records


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
