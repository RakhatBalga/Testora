"""Google Gemini transport and graders.

Used when AI_PROVIDER=gemini and GEMINI_API_KEY is set (see factory.py).
The `google-genai` package is imported lazily so the app runs without it
installed while on the mock provider.

Only the transport is Gemini-specific. Prompts, schema, temperature, seed and
the scoring rules are shared with every provider through `engine.py`.

Gemini is multimodal, so the Speaking grader sends the recorded audio file
directly to the model -- no separate speech-to-text step is required.
"""

import logging
import time
from pathlib import Path

from app.domain.grading import Feedback, grading_error_feedback
from app.infrastructure.config import settings
from app.infrastructure.ai import prompts
from app.infrastructure.ai.base import SpeakingGrader, WritingGrader
from app.infrastructure.ai.engine import (
    EXAMINER_MAX_TOKENS,
    EXAMINER_TEMPERATURE,
    GRADING_SEED,
    ROLE_EXAMINER,
    SCHEMA_ATTEMPTS,
    TransportVocabularyCoach,
    WritingEngine,
    extract_json_text,
    parse_json_object,
)
from app.infrastructure.ai.retry import (
    DEFAULT_POLICY,
    RetryPolicy,
    SchemaError,
    TruncatedResponse,
    is_transient_status,
    parse_retry_after,
)
from app.infrastructure.ai.schemas import SpeakingExaminer, speaking_feedback

logger = logging.getLogger("testora.ai.gemini")

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

# Backward-compatible alias (tests and callers used the private name).
_TruncatedResponse = TruncatedResponse


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
    temperature: float = EXAMINER_TEMPERATURE,
    max_tokens: int = 4096,
    model: str | None = None,
    json_mode: bool = True,
):
    from google.genai import types

    kwargs = dict(
        system_instruction=system,
        # Headroom so a full criterion-level rubric + errors never gets truncated
        # mid-JSON. The examiner prompt is intentionally detailed; Pro models also
        # spend output tokens on required thinking. A truncated body is surfaced as
        # a grading error, never saved as a bogus grade.
        max_output_tokens=max_tokens,
        temperature=temperature,
        seed=GRADING_SEED,
    )
    if json_mode:
        kwargs["response_mime_type"] = "application/json"
    # Gemini Flash supports disabling thinking, which keeps structured grading
    # cheaper and more deterministic. Gemini Pro requires thinking mode, so do
    # not send an invalid zero budget for Pro models.
    if "pro" not in (model or settings.GEMINI_MODEL).lower():
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    if schema is not None:
        kwargs["response_schema"] = schema
    return types.GenerateContentConfig(**kwargs)


def _raise_if_truncated(resp) -> None:
    """Detect a MAX_TOKENS finish so we never parse half-written JSON."""
    candidates = getattr(resp, "candidates", None) or []
    for cand in candidates:
        reason = getattr(cand, "finish_reason", None)
        if reason is not None and str(reason).upper().endswith("MAX_TOKENS"):
            raise TruncatedResponse("Gemini response was truncated at the output-token limit")


def _classify(exc: Exception) -> tuple[bool, float | None]:
    """(transient?, retry_after seconds) for an exception from the SDK call."""
    try:
        from google.genai import errors as genai_errors
    except ImportError:  # pragma: no cover - SDK is a hard dependency
        genai_errors = None
    if genai_errors is not None and isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        if isinstance(code, int) and is_transient_status(code):
            headers = getattr(getattr(exc, "response", None), "headers", None) or {}
            try:
                retry_after = parse_retry_after(headers.get("retry-after"))
            except AttributeError:
                retry_after = None
            return True, retry_after
        return False, None
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True, None
    try:
        import httpx
    except ImportError:  # pragma: no cover
        return False, None
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True, None
    return False, None


def _generate(
    contents,
    system: str,
    *,
    schema=None,
    temperature: float = EXAMINER_TEMPERATURE,
    max_tokens: int = 4096,
    model: str | None = None,
    json_mode: bool = True,
    policy: RetryPolicy = DEFAULT_POLICY,
) -> str:
    """Call Gemini with a fresh client; retry only transient failures."""
    used_model = model or settings.GEMINI_MODEL
    if "pro" in used_model.lower():
        max_tokens = max(max_tokens, 8192)
    attempt = 0
    while True:
        attempt += 1
        try:
            client = _client()
            resp = client.models.generate_content(
                model=used_model,
                contents=contents,
                config=_config(
                    system,
                    schema=schema,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=used_model,
                    json_mode=json_mode,
                ),
            )
            _raise_if_truncated(resp)
            text = resp.text
            if not text or not text.strip():
                raise SchemaError("Gemini returned an empty response")
            return text
        except (TruncatedResponse, SchemaError):
            raise
        except Exception as exc:  # noqa: BLE001 - classified, retried or surfaced
            transient, retry_after = _classify(exc)
            delay = policy.delay(attempt, retry_after) if transient else None
            logger.warning(
                "Gemini generate_content attempt %d/%d failed (%s): %s",
                attempt,
                policy.max_attempts,
                "transient" if transient else "permanent",
                exc,
            )
            if delay is None:
                raise
            time.sleep(delay)


def _json_text(raw: str) -> str:
    """Return clean JSON text, stripping any markdown code fence the model added."""
    return extract_json_text(raw)


def _parse(raw: str) -> dict:
    return parse_json_object(raw)


class GeminiTransport:
    provider = "gemini"

    def model_for(self, role: str) -> str:
        return settings.GEMINI_MODEL if role == ROLE_EXAMINER else settings.GEMINI_FAST_MODEL

    def generate_json(self, *, role, system, user, schema, temperature, max_tokens) -> str:
        return _generate(
            [user],
            system,
            schema=schema,
            temperature=temperature,
            max_tokens=max_tokens,
            model=self.model_for(role),
        )

    def generate_text(self, *, role, system, user, temperature, max_tokens) -> str:
        return _generate(
            [user],
            system,
            temperature=temperature,
            max_tokens=max_tokens,
            model=self.model_for(role),
            json_mode=False,
        )


class GeminiWritingGrader(WritingGrader):
    """Two-stage IELTS Writing engine (shared method) over the Gemini transport."""

    def __init__(self):
        self.engine = WritingEngine(GeminiTransport(), coach_enabled=settings.WRITING_COACH_ENABLED)

    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        self.engine.coach_enabled = settings.WRITING_COACH_ENABLED
        return self.engine.grade(task_type=task_type, prompt=prompt, text=text, min_words=min_words)

    def improve(self, *, task_type: int, prompt: str, text: str) -> str | None:
        return self.engine.improve(task_type=task_type, prompt=prompt, text=text)


class GeminiSpeakingGrader(SpeakingGrader):
    """Audio-in grading. Same schema and normalisation as the transcript path;
    snippets are cleared because they cannot be checked against audio."""

    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback:
        from google.genai import types

        model = settings.GEMINI_MODEL
        try:
            path = Path(audio_path)
            mime = _AUDIO_MIME.get(path.suffix.lower(), "audio/webm")
            audio_bytes = path.read_bytes()
            contents = [
                types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                prompts.speaking_user_prompt(part=part, questions=questions),
            ]
            result = None
            for attempt in range(1, SCHEMA_ATTEMPTS + 1):
                try:
                    raw = _generate(
                        contents,
                        prompts.SPEAKING_AUDIO_SYSTEM,
                        schema=SpeakingExaminer,
                        temperature=EXAMINER_TEMPERATURE,
                        max_tokens=EXAMINER_MAX_TOKENS,
                        model=model,
                    )
                    result = SpeakingExaminer.model_validate_json(_json_text(raw))
                    break
                except (SchemaError, ValueError) as exc:
                    logger.warning("Gemini speaking output invalid (attempt %d): %s", attempt, exc)
            if result is None:
                raise SchemaError("speaking output invalid")
            feedback = speaking_feedback(result, transcript=None)
        except Exception:  # noqa: BLE001
            logger.exception("Gemini speaking grading failed")
            feedback = grading_error_feedback()
        feedback.provider = "gemini"
        feedback.model = model
        feedback.prompt_version = prompts.prompt_version()
        return feedback


class GeminiVocabularyCoach(TransportVocabularyCoach):
    """Word enrichment + practice-quiz generation. Uses the fast model — this is
    prose/lookup work, not band scoring, so Flash quality is fine and cheaper."""

    def __init__(self):
        super().__init__(GeminiTransport())
