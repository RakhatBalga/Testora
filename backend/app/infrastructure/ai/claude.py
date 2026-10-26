"""Claude transport and graders — EXPERIMENTAL.

Used only when AI_PROVIDER=claude and a key is set (see factory.py). Not used
in production and not exercised against the live API in CI. It goes through
the same engine as Gemini and Qwen (prompts, schema, temperature, scoring
rules), so a comparison measures the model, not a different prompt.

Differences that remain: the Messages API has no `seed` and no schema-
constrained output here, so the JSON schema is appended to the system prompt
and validated locally (one re-ask on failure). The model id is not verified.
The `anthropic` package is imported lazily and is not in requirements.txt.
"""
import json
import logging
import time

from app.domain.grading import Feedback
from app.infrastructure.config import settings
from app.infrastructure.ai.base import SpeakingGrader, WritingGrader
from app.infrastructure.ai.engine import (
    TransportVocabularyCoach,
    WritingEngine,
    grade_speaking_transcript,
    speaking_unsupported_feedback,
)
from app.infrastructure.ai.retry import DEFAULT_POLICY, is_transient_status

logger = logging.getLogger("testora.ai.claude")

MODEL = "claude-sonnet-4-6"


def _client():
    from anthropic import Anthropic  # lazy import

    # SDK retries off: the shared policy below decides what is transient.
    return Anthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=0, timeout=60.0)


def _transient(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return is_transient_status(status)
    name = type(exc).__name__
    return name in {"APITimeoutError", "APIConnectionError"} or isinstance(exc, (TimeoutError, ConnectionError))


class ClaudeTransport:
    provider = "claude"

    def model_for(self, role: str) -> str:
        return MODEL

    def _ask(self, system: str, user: str, *, temperature: float, max_tokens: int) -> str:
        attempt = 0
        while True:
            attempt += 1
            try:
                msg = _client().messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return "".join(getattr(block, "text", "") for block in msg.content)
            except Exception as exc:  # noqa: BLE001 - classified below
                delay = DEFAULT_POLICY.delay(attempt) if _transient(exc) else None
                logger.warning("Claude call attempt %d failed: %s", attempt, exc)
                if delay is None:
                    raise
                time.sleep(delay)

    def generate_json(self, *, role, system, user, schema, temperature, max_tokens) -> str:
        system = (
            f"{system}\n\nReturn ONLY one JSON object that validates against this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema(), separators=(',', ':'))}"
        )
        return self._ask(system, user, temperature=temperature, max_tokens=max_tokens)

    def generate_text(self, *, role, system, user, temperature, max_tokens) -> str:
        return self._ask(system, user, temperature=temperature, max_tokens=max_tokens)


class ClaudeWritingGrader(WritingGrader):
    def __init__(self):
        self.engine = WritingEngine(ClaudeTransport(), coach_enabled=settings.WRITING_COACH_ENABLED)

    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        return self.engine.grade(task_type=task_type, prompt=prompt, text=text, min_words=min_words)

    def improve(self, *, task_type: int, prompt: str, text: str) -> str | None:
        return self.engine.improve(task_type=task_type, prompt=prompt, text=text)


class ClaudeSpeakingGrader(SpeakingGrader):
    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback:
        transport = ClaudeTransport()
        if not (transcript or "").strip():
            return speaking_unsupported_feedback(transport)
        return grade_speaking_transcript(transport, part=part, questions=questions, transcript=transcript)


class ClaudeVocabularyCoach(TransportVocabularyCoach):
    def __init__(self):
        super().__init__(ClaudeTransport())
