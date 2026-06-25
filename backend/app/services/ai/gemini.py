"""Google Gemini-based graders.

Used when AI_PROVIDER=gemini and GEMINI_API_KEY is set (see factory.py).
The `google-genai` package is imported lazily so the app runs without it
installed while on the mock provider.

Gemini is multimodal, so the Speaking grader sends the recorded audio file
directly to the model -- no separate speech-to-text step is required.
"""

import json
import logging
import re
import time
from pathlib import Path

from app.core.config import settings
from app.services.ai import prompts
from app.services.ai.base import Feedback, SpeakingGrader, WritingGrader
from app.services.ai.schemas import (
    CoachResult,
    build_feedback,
    examiner_model,
    normalize_examiner,
)

logger = logging.getLogger("testora.ai.gemini")

# Examiner runs cold for consistency; coach a little warmer for natural prose.
_EXAMINER_TEMPERATURE = 0.1
_COACH_TEMPERATURE = 0.35

# Retry policy for transient Gemini failures (timeouts, 5xx, connection resets).
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 1.0

# How long to wait for the model to respond, in milliseconds. The default
# httpx timeout is too short for full IELTS grading.
_HTTP_TIMEOUT_MS = 60_000

# Map saved-file extensions to the audio MIME types Gemini accepts.
_AUDIO_MIME = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/aac",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}

_SPEAKING_SYSTEM = (
    "You are an experienced IELTS examiner. Listen to the candidate's recorded "
    "spoken response and grade it using the official IELTS band descriptors "
    "(0-9, half-bands allowed) for four criteria: Fluency & Coherence, "
    "Lexical Resource, Grammatical Range & Accuracy, Pronunciation. "
    "Base Pronunciation and Fluency on the actual audio. Respond ONLY with a JSON "
    'object of the form: {"band": number, "criteria": {"Fluency & Coherence": '
    'number, "Lexical Resource": number, "Grammatical Range & Accuracy": number, '
    '"Pronunciation": number}, "summary": string, "suggestions": [string, ...]}.'
)


class _TruncatedResponse(Exception):
    """The model stopped because it hit the output-token cap; output is unusable."""


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def _client():
    from google import genai  # lazy import
    from google.genai import types

    # attempts=1 disables SDK retry, which can reuse a closed httpx connection.
    # We retry ourselves with a fresh client in _generate().
    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=_HTTP_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _config(
    system: str,
    *,
    schema=None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
):
    from google.genai import types

    kwargs = dict(
        system_instruction=system,
        response_mime_type="application/json",
        # Headroom so a full criterion-level rubric + errors never gets truncated
        # mid-JSON. A truncated body is surfaced as a grading error, never saved
        # as a bogus grade.
        max_output_tokens=max_tokens,
        temperature=temperature,
        # gemini-2.5-* thinking tokens count against max_output_tokens. Disable
        # them for deterministic structured grading.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    if schema is not None:
        kwargs["response_schema"] = schema
    return types.GenerateContentConfig(**kwargs)


def _raise_if_truncated(resp) -> None:
    """Detect a MAX_TOKENS finish so we never parse half-written JSON."""
    candidates = getattr(resp, "candidates", None) or []
    for cand in candidates:
        reason = getattr(cand, "finish_reason", None)
        if reason is not None and str(reason).upper().endswith("MAX_TOKENS"):
            raise _TruncatedResponse(
                "Gemini response was truncated at the output-token limit"
            )


def _generate(
    contents,
    system: str,
    *,
    schema=None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Call Gemini with a fresh client, retrying transient failures with backoff."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            client = _client()
            resp = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=_config(
                    system,
                    schema=schema,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )
            _raise_if_truncated(resp)
            text = resp.text
            if not text or not text.strip():
                raise ValueError("Gemini returned an empty response")
            return text
        except _TruncatedResponse:
            raise
        except Exception as exc:  # noqa: BLE001 - retried, then surfaced
            last_exc = exc
            logger.warning(
                "Gemini generate_content attempt %d/%d failed: %s",
                attempt,
                _MAX_ATTEMPTS,
                exc,
            )
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
    raise last_exc  # type: ignore[misc]


def _json_text(raw: str) -> str:
    """Return clean JSON text, stripping any markdown code fence the model added."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Gemini returned an empty response")
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    return raw


def _parse(raw: str) -> dict:
    data = json.loads(_json_text(raw))
    if not isinstance(data, dict):
        raise ValueError("Gemini response was not a JSON object")
    return data


def _to_feedback(data: dict) -> Feedback:
    criteria = {k: float(v) for k, v in data.get("criteria", {}).items()}
    band = float(
        data.get("band")
        or (sum(criteria.values()) / len(criteria) if criteria else 0)
    )
    return Feedback(
        band=band,
        criteria=criteria,
        summary=str(data.get("summary", "")),
        suggestions=[str(s) for s in data.get("suggestions", [])],
    )


def _error_feedback(message: str) -> Feedback:
    """Return failed-grading feedback without persisting a bogus Band-0 grade."""
    return Feedback(
        band=0.0,
        criteria={},
        summary=f"Automatic grading could not be completed: {message}",
        suggestions=["Try submitting again, or check the AI configuration."],
        error=True,
    )


class GeminiWritingGrader(WritingGrader):
    """Two-stage IELTS Writing engine: cold Examiner, then warmer Coach."""

    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        word_count = _count_words(text)
        system = (
            prompts.TASK1_EXAMINER_SYSTEM
            if task_type == 1
            else prompts.TASK2_EXAMINER_SYSTEM
        )
        user = prompts.examiner_user_prompt(
            task_type=task_type,
            prompt=prompt,
            text=text,
            min_words=min_words,
            word_count=word_count,
        )
        model = examiner_model(task_type)
        try:
            raw = _generate(
                [user],
                system,
                schema=model,
                temperature=_EXAMINER_TEMPERATURE,
            )
            examiner = model.model_validate_json(_json_text(raw))
        except Exception as exc:  # noqa: BLE001 - never 500 the submit endpoint
            logger.exception("Gemini Writing examiner stage failed")
            return _error_feedback(str(exc))

        normalized = normalize_examiner(
            examiner,
            task_type=task_type,
            word_count=word_count,
            min_words=min_words,
        )
        coaching = (
            self._coach(task_type, prompt, text, examiner)
            if settings.WRITING_COACH_ENABLED
            else None
        )
        return build_feedback(normalized, coaching, task_type=task_type)

    def _coach(self, task_type, prompt, text, examiner) -> CoachResult | None:
        """Best-effort coaching; a failure here must not fail the grade."""
        try:
            user = prompts.coach_user_prompt(
                task_type=task_type,
                prompt=prompt,
                text=text,
                examiner_json=examiner.model_dump_json(),
            )
            raw = _generate(
                [user],
                prompts.COACH_SYSTEM,
                schema=CoachResult,
                temperature=_COACH_TEMPERATURE,
                max_tokens=1536,
            )
            return CoachResult.model_validate_json(_json_text(raw))
        except Exception:  # noqa: BLE001
            logger.warning(
                "Gemini Writing coach stage failed; returning examiner result only",
                exc_info=True,
            )
            return None


class GeminiSpeakingGrader(SpeakingGrader):
    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback:
        from google.genai import types

        joined = "\n".join(f"- {q}" for q in questions)
        prompt = (
            f"IELTS Speaking Part {part}.\n\nQUESTIONS:\n{joined}\n\n"
            "Grade the attached audio recording of the candidate's answer."
        )
        try:
            path = Path(audio_path)
            mime = _AUDIO_MIME.get(path.suffix.lower(), "audio/webm")
            audio_bytes = path.read_bytes()
            contents = [
                types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                prompt,
            ]
            raw = _generate(contents, _SPEAKING_SYSTEM)
            return _to_feedback(_parse(raw))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini speaking grading failed")
            return _error_feedback(str(exc))
