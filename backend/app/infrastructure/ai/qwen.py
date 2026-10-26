"""Self-hosted Qwen graders over an OpenAI-compatible API.

Used when AI_PROVIDER=qwen with QWEN_BASE_URL and QWEN_MODEL set (factory.py).
The server can be Ollama / LM Studio / MLX on the owner's Mac or vLLM/SGLang on
a rented GPU; see docs/qwen.md. Prompts, schema, temperature, seed and scoring
rules are the shared ones from `engine.py`, so only the model changes.

Speaking: Qwen text models cannot hear audio. Grading works from a transcript
(`grade(..., transcript=...)`). Until an ASR step (Whisper) produces one, a
Speaking submission fails cleanly with "not supported on this provider yet".
Planned path: faster-whisper ASR -> this transcript grader; later possibly a
Qwen-Omni audio model behind the same interface.
"""

from __future__ import annotations

from app.domain.grading import Feedback
from app.infrastructure.config import settings
from app.infrastructure.ai.base import SpeakingGrader, WritingGrader
from app.infrastructure.ai.engine import (
    GRADING_SEED,
    TransportVocabularyCoach,
    WritingEngine,
    grade_speaking_transcript,
    speaking_unsupported_feedback,
)
from app.infrastructure.ai.openai_compat import OpenAICompatClient, run_sync


def _client() -> OpenAICompatClient:
    return OpenAICompatClient(
        base_url=settings.QWEN_BASE_URL,
        model=settings.QWEN_MODEL,
        api_key=settings.QWEN_API_KEY or None,
        timeout=settings.QWEN_TIMEOUT_SECONDS,
        disable_thinking=settings.QWEN_DISABLE_THINKING,
    )


class QwenTransport:
    """One model for every role (examiner, coach, rewrite, vocabulary)."""

    provider = "qwen"

    def __init__(self, client: OpenAICompatClient | None = None):
        self.client = client or _client()

    def model_for(self, role: str) -> str:
        return self.client.model

    def generate_json(self, *, role, system, user, schema, temperature, max_tokens) -> str:
        return run_sync(
            lambda: self.client.chat_json(
                system=system,
                user=user,
                schema=schema,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=GRADING_SEED,
            )
        )

    def generate_text(self, *, role, system, user, temperature, max_tokens) -> str:
        return run_sync(
            lambda: self.client.chat_text(
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=GRADING_SEED,
            )
        )


class QwenWritingGrader(WritingGrader):
    def __init__(self, transport: QwenTransport | None = None):
        self.engine = WritingEngine(transport or QwenTransport(), coach_enabled=settings.WRITING_COACH_ENABLED)

    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        return self.engine.grade(task_type=task_type, prompt=prompt, text=text, min_words=min_words)

    def improve(self, *, task_type: int, prompt: str, text: str) -> str | None:
        return self.engine.improve(task_type=task_type, prompt=prompt, text=text)


class QwenSpeakingGrader(SpeakingGrader):
    def __init__(self, transport: QwenTransport | None = None):
        self.transport = transport or QwenTransport()

    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback:
        if not (transcript or "").strip():
            return speaking_unsupported_feedback(self.transport)
        return grade_speaking_transcript(self.transport, part=part, questions=questions, transcript=transcript)


class QwenVocabularyCoach(TransportVocabularyCoach):
    def __init__(self, transport: QwenTransport | None = None):
        super().__init__(transport or QwenTransport())


def _tagless(name: str) -> str:
    return name[: -len(":latest")] if name.endswith(":latest") else name


def model_listed(model: str, models: list[str]) -> bool:
    """Exact match, or Ollama's implicit tag: "qwen3" == "qwen3:latest"."""
    return model in models or _tagless(model) in {_tagless(m) for m in models}


async def ping_qwen(client: OpenAICompatClient | None = None) -> dict:
    """Readiness probe for the Qwen server: GET {QWEN_BASE_URL}/models.

    Returns {"ok", "model", "model_available", "error"}; never raises and
    never includes the API key or raw server text.
    """
    client = client or _client()
    try:
        models = await client.list_models()
    except Exception as exc:  # noqa: BLE001 - health checks report, never raise
        return {"ok": False, "model": client.model, "model_available": False, "error": type(exc).__name__}
    return {
        "ok": True,
        "model": client.model,
        "model_available": model_listed(client.model, models),
        "error": None,
    }
