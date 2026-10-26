"""Provider-agnostic grading engine.

One scoring method for every provider: the same prompts, the same JSON schema,
the same temperature/seed, and the same deterministic normalisation
(`app.domain.grading`). A provider only supplies a `Transport` that turns
(system, user, schema) into raw text. So switching Gemini -> Qwen changes the
model, not the method, and "Gemini vs Qwen" comparisons compare models.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Protocol

from pydantic import BaseModel, ValidationError

from app.domain.grading import (
    Feedback,
    grading_error_feedback,
    validate_writing_submission,
    zero_band_feedback,
)
from app.infrastructure.ai import prompts
from app.infrastructure.ai import vocab
from app.infrastructure.ai.retry import SchemaError
from app.infrastructure.ai.schemas import (
    CoachResult,
    SpeakingExaminer,
    build_feedback,
    examiner_model,
    normalize_examiner,
    sanitize_coach_evidence,
    speaking_feedback,
)

logger = logging.getLogger("testora.ai.engine")

# Identical across providers so a provider comparison is not a temperature
# comparison. Examiner runs cold for consistency; coach a little warmer.
EXAMINER_TEMPERATURE = 0.1
COACH_TEMPERATURE = 0.35
BETTER_VERSION_TEMPERATURE = 0.4
VOCAB_ENRICH_TEMPERATURE = 0.3
VOCAB_QUIZ_TEMPERATURE = 0.5
# Passed wherever the API supports it (Gemini, OpenAI-compatible servers).
# Best-effort determinism only: servers may still vary between runs.
GRADING_SEED = 20261026

EXAMINER_MAX_TOKENS = 4096
COACH_MAX_TOKENS = 1536
BETTER_VERSION_MAX_TOKENS = 2048

# Examiner/coach/speaking: one extra attempt when the reply is not valid JSON
# for the schema. Transport-level retries (timeouts, 5xx, 429) are separate.
SCHEMA_ATTEMPTS = 2

ROLE_EXAMINER = "examiner"
ROLE_COACH = "coach"
ROLE_REWRITE = "rewrite"
ROLE_VOCAB = "vocab"


class Transport(Protocol):
    """What a provider must implement. Synchronous; graders run in a threadpool."""

    provider: str

    def model_for(self, role: str) -> str: ...

    def generate_json(
        self,
        *,
        role: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Return the raw model text, expected to be one JSON object."""
        ...

    def generate_text(
        self,
        *,
        role: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> str: ...


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> str:
    """Remove reasoning blocks (Qwen3 / R1 style) from a reply.

    Handles complete <think>...</think> blocks, a reply that starts mid-thought
    and only has the closing tag, and an unterminated opening tag.
    """
    text = _THINK_BLOCK_RE.sub("", text or "")
    lower = text.lower()
    if "</think>" in lower:
        text = text[lower.rindex("</think>") + len("</think>") :]
    elif "<think>" in lower:
        text = text[: lower.index("<think>")]
    return text.strip()


def extract_json_text(raw: str) -> str:
    """Return clean JSON text: no reasoning, no markdown fence, no prose around it."""
    text = strip_think(raw)
    if not text:
        raise SchemaError("model returned an empty response")
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise SchemaError("model response contained no JSON object")
    return text[start : end + 1]


def parse_json_object(raw: str) -> dict:
    try:
        data = json.loads(extract_json_text(raw))
    except json.JSONDecodeError as exc:
        raise SchemaError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise SchemaError("model response was not a JSON object")
    return data


def ask_structured(
    transport: Transport,
    *,
    role: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    temperature: float,
    max_tokens: int,
    attempts: int = SCHEMA_ATTEMPTS,
) -> BaseModel:
    """Call the transport and validate against `schema`, re-asking once."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            raw = transport.generate_json(
                role=role,
                system=system,
                user=user,
                schema=schema,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return schema.model_validate_json(extract_json_text(raw))
        except (ValidationError, SchemaError) as exc:
            last = exc
            logger.warning(
                "%s %s output failed schema validation (attempt %d/%d): %s",
                transport.provider,
                role,
                attempt,
                attempts,
                exc,
            )
    raise SchemaError(f"{role} output invalid after {attempts} attempts") from last


class WritingEngine:
    """Two-stage IELTS Writing engine: cold Examiner, then warmer Coach."""

    def __init__(self, transport: Transport, *, coach_enabled: bool = True):
        self.transport = transport
        self.coach_enabled = coach_enabled

    def _provenance(self, feedback: Feedback, version: str) -> Feedback:
        feedback.provider = self.transport.provider
        feedback.model = self.transport.model_for(ROLE_EXAMINER)
        feedback.prompt_version = prompts.prompt_version(version)
        return feedback

    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        # Resolve once so the recorded version is the one that actually ran.
        version = prompts.active_examiner_version()
        precheck = validate_writing_submission(task_type=task_type, text=text, min_words=min_words)
        if not precheck.valid:
            return self._provenance(zero_band_feedback(task_type, precheck), version)
        word_count = precheck.word_count

        system = prompts.examiner_system(task_type, version)
        user = prompts.examiner_user_prompt(
            task_type=task_type,
            prompt=prompt,
            text=text,
            min_words=min_words,
            word_count=word_count,
        )
        try:
            examiner = ask_structured(
                self.transport,
                role=ROLE_EXAMINER,
                system=system,
                user=user,
                schema=examiner_model(task_type),
                temperature=EXAMINER_TEMPERATURE,
                max_tokens=EXAMINER_MAX_TOKENS,
            )
        except Exception:  # noqa: BLE001 - never 500 the submit endpoint
            logger.exception("%s Writing examiner stage failed", self.transport.provider)
            return grading_error_feedback(
                provider=self.transport.provider,
                model=self.transport.model_for(ROLE_EXAMINER),
                prompt_version=prompts.prompt_version(version),
            )

        normalized = normalize_examiner(
            examiner,
            task_type=task_type,
            word_count=word_count,
            min_words=min_words,
            text=text,
            prompt=prompt,
        )
        coaching = self._coach(task_type, prompt, text, examiner, normalized["overall"]) if self.coach_enabled else None
        feedback = build_feedback(normalized, coaching, task_type=task_type, text=text)
        return self._provenance(feedback, version)

    def _coach(self, task_type, prompt, text, examiner, current_overall) -> CoachResult | None:
        """Best-effort coaching; a failure here must not fail the grade."""
        try:
            user = prompts.coach_user_prompt(
                task_type=task_type,
                prompt=prompt,
                text=text,
                examiner_json=examiner.model_dump_json(),
                current_overall=current_overall,
            )
            coaching = ask_structured(
                self.transport,
                role=ROLE_COACH,
                system=prompts.COACH_SYSTEM,
                user=user,
                schema=CoachResult,
                temperature=COACH_TEMPERATURE,
                max_tokens=COACH_MAX_TOKENS,
            )
            return sanitize_coach_evidence(coaching, essay=text, errors=examiner.errors)
        except Exception:  # noqa: BLE001
            logger.warning(
                "%s Writing coach stage failed; returning examiner result only",
                self.transport.provider,
                exc_info=True,
            )
            return None

    def improve(self, *, task_type: int, prompt: str, text: str) -> str | None:
        """Best-effort "Better Version"; None lets the UI use its diff engine."""
        try:
            out = self.transport.generate_text(
                role=ROLE_REWRITE,
                system=prompts.BETTER_VERSION_SYSTEM,
                user=prompts.better_version_user_prompt(task_type=task_type, prompt=prompt, text=text),
                temperature=BETTER_VERSION_TEMPERATURE,
                max_tokens=BETTER_VERSION_MAX_TOKENS,
            )
            out = strip_think(out)
            return out or None
        except Exception:  # noqa: BLE001 - never fail the submit endpoint
            logger.exception("%s Better Version generation failed", self.transport.provider)
            return None


def grade_speaking_transcript(
    transport: Transport,
    *,
    part: int,
    questions: list[str],
    transcript: str,
) -> Feedback:
    """Text-only Speaking grading (for providers without audio input)."""
    try:
        result = ask_structured(
            transport,
            role=ROLE_EXAMINER,
            system=prompts.SPEAKING_TRANSCRIPT_SYSTEM,
            user=prompts.speaking_user_prompt(part=part, questions=questions, transcript=transcript),
            schema=SpeakingExaminer,
            temperature=EXAMINER_TEMPERATURE,
            max_tokens=EXAMINER_MAX_TOKENS,
        )
        feedback = speaking_feedback(result, transcript=transcript)
    except Exception:  # noqa: BLE001
        logger.exception("%s Speaking grading failed", transport.provider)
        feedback = grading_error_feedback()
    feedback.provider = transport.provider
    feedback.model = transport.model_for(ROLE_EXAMINER)
    feedback.prompt_version = prompts.prompt_version()
    return feedback


SPEAKING_UNSUPPORTED_MESSAGE = (
    "Speaking assessment is not supported on this AI provider yet: it needs a "
    "transcript of the recording. Your recording was saved."
)


def speaking_unsupported_feedback(transport: Transport) -> Feedback:
    return grading_error_feedback(
        provider=transport.provider,
        model=transport.model_for(ROLE_EXAMINER),
        prompt_version=prompts.prompt_version(),
        message=SPEAKING_UNSUPPORTED_MESSAGE,
    )


class TransportVocabularyCoach(vocab.VocabularyCoach):
    """Word enrichment + practice quizzes over any transport (prose, not scoring)."""

    def __init__(self, transport: Transport):
        self.transport = transport

    def enrich_word(self, *, word: str, context: str | None, native_language: str | None) -> vocab.WordInfo:
        try:
            data = ask_structured(
                self.transport,
                role=ROLE_VOCAB,
                system=vocab.ENRICH_SYSTEM,
                user=vocab.enrich_user_prompt(word=word, context=context, native_language=native_language),
                schema=vocab.WordInfoSchema,
                temperature=VOCAB_ENRICH_TEMPERATURE,
                max_tokens=1024,
                attempts=1,
            )
            return vocab.word_info_from_schema(word, data)
        except Exception:  # noqa: BLE001 - degrade, never 500 the endpoint
            logger.exception("%s word enrichment failed for %r", self.transport.provider, word)
            return vocab.WordInfo(word=word, error=True)

    def generate_quiz(self, *, words: list[dict], native_language: str | None, num_questions: int) -> vocab.WordQuiz:
        try:
            data = ask_structured(
                self.transport,
                role=ROLE_VOCAB,
                system=vocab.QUIZ_SYSTEM,
                user=vocab.quiz_user_prompt(words=words, native_language=native_language, num_questions=num_questions),
                schema=vocab.QuizSchema,
                temperature=VOCAB_QUIZ_TEMPERATURE,
                max_tokens=2048,
                attempts=1,
            )
            return vocab.quiz_from_schema(data, num_questions)
        except Exception:  # noqa: BLE001
            logger.exception("%s quiz generation failed", self.transport.provider)
            return vocab.WordQuiz(error=True)
