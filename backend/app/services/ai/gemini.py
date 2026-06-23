"""Google Gemini-based graders.

Used when AI_PROVIDER=gemini and GEMINI_API_KEY is set (see factory.py).
The `google-genai` package is imported lazily so the app runs without it
installed while on the mock provider.

Writing grading produces the full IELTS criterion breakdown plus strengths,
weaknesses, atomic mistakes and improvement actions. Every Gemini call is
wrapped so that on ANY failure (timeout, quota, invalid JSON, missing scores)
we log the error and fall back to the deterministic MockProvider — the user
always receives a result.

Gemini is multimodal, so the Speaking grader sends the recorded audio file
directly to the model — no separate speech-to-text step is required.
"""

import json
import logging
from pathlib import Path

from app.core.config import settings
from app.services.ai.base import Feedback, MistakeItem, WritingGrader, SpeakingGrader
from app.services.ai.mock import MockWritingGrader, MockSpeakingGrader
from app.services.ai.prompts import (
    WRITING_SYSTEM,
    SPEAKING_SYSTEM,
    build_writing_user_prompt,
    build_speaking_user_prompt,
)

logger = logging.getLogger("testora.ai.gemini")

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

# How long to wait for the model to respond, in milliseconds. The default
# httpx timeout is too short for full IELTS grading: the first request times
# out, and the SDK's internal retry then fails with "client has been closed".
_HTTP_TIMEOUT_MS = 60_000


def _client():
    from google import genai  # lazy import
    from google.genai import types

    # attempts=1 disables the SDK's built-in retry, which reuses a closed httpx
    # connection and fails with "client has been closed". We retry ourselves in
    # _generate() with a fresh client instead.
    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=_HTTP_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _config(system: str, max_output_tokens: int = 2048):
    from google.genai import types

    return types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        max_output_tokens=max_output_tokens,
        temperature=0.3,
        # gemini-2.5-* are thinking models whose reasoning tokens count against
        # max_output_tokens. Left on, thinking eats the whole budget and the JSON
        # is truncated (FinishReason.MAX_TOKENS). Disable it for deterministic
        # structured grading — we want the answer, not visible reasoning.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )


def _generate(contents, system: str, max_output_tokens: int = 2048) -> str:
    """Call Gemini with a fresh client, retrying once on transient failures.

    Each attempt builds a new client because the SDK's internal retry reuses a
    closed httpx connection; a fresh client sidesteps that.
    """
    last_exc: Exception | None = None
    for _ in range(2):
        try:
            # Hold the client in a local: passing `_client().models...` inline lets
            # the temporary Client be GC'd mid-call, which closes its httpx
            # transport ("client has been closed").
            client = _client()
            resp = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=_config(system, max_output_tokens),
            )
            return resp.text
        except Exception as exc:  # noqa: BLE001 — retried, then surfaced
            last_exc = exc
    raise last_exc  # type: ignore[misc]


# ── Parsing & validation ─────────────────────────────────────────────────────

def _parse(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Gemini returned an empty response")
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Gemini response was not a JSON object")
    return data


def _round_half(x: float) -> float:
    x = max(0.0, min(9.0, x))
    return round(x * 2) / 2


def _coerce_band(value, default: float = 0.0) -> float:
    try:
        return _round_half(float(value))
    except (TypeError, ValueError):
        return default


def _str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


# Normalise Gemini's free-text mistake categories into the fixed taxonomy the
# mistakes table + analytics expect (grammar | vocabulary | coherence |
# task_response). Keeps Mistake Memory / Weakness / Recommendation engines working.
_CATEGORY_MAP = {
    "grammar": "grammar",
    "grammatical": "grammar",
    "grammatical range and accuracy": "grammar",
    "grammatical range & accuracy": "grammar",
    "spelling": "grammar",
    "punctuation": "grammar",
    "vocabulary": "vocabulary",
    "lexical": "vocabulary",
    "lexical resource": "vocabulary",
    "word choice": "vocabulary",
    "collocation": "vocabulary",
    "coherence": "coherence",
    "cohesion": "coherence",
    "coherence and cohesion": "coherence",
    "coherence & cohesion": "coherence",
    "structure": "coherence",
    "organization": "coherence",
    "organisation": "coherence",
    "linking": "coherence",
    "task": "task_response",
    "task response": "task_response",
    "task achievement": "task_response",
    "relevance": "task_response",
}


def _normalize_category(raw: str) -> str:
    key = (raw or "").strip().lower()
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    for token, cat in _CATEGORY_MAP.items():
        if token in key:
            return cat
    return "grammar"  # safe default — keeps the row inside the known taxonomy


def _parse_mistakes(raw) -> list[MistakeItem]:
    out: list[MistakeItem] = []
    if not isinstance(raw, list):
        return out
    for m in raw:
        if not isinstance(m, dict):
            continue
        explanation = str(m.get("explanation", "")).strip() or None
        snippet = str(m.get("snippet", "")).strip() or None
        if not explanation and not snippet:
            continue
        out.append(
            MistakeItem(
                category=_normalize_category(str(m.get("category", ""))),
                subskill=None,
                severity=2,  # Gemini gives no severity; treat as moderate
                snippet=snippet,
                correction=None,
                explanation=explanation,
            )
        )
    return out


def _build_summary(band: float, strengths: list[str], weaknesses: list[str]) -> str:
    parts = [f"Estimated overall Band {band:.1f}."]
    if strengths:
        parts.append(f"Strength: {strengths[0]}")
    if weaknesses:
        parts.append(f"Focus next on: {weaknesses[0]}")
    return " ".join(parts)


def _validate_writing(data: dict) -> Feedback:
    """Turn Gemini's writing JSON into a validated Feedback, or raise on garbage.

    Criterion keys use the canonical names the analytics layer already maps
    (Task Response, Coherence & Cohesion, Lexical Resource, Grammatical Range &
    Accuracy), so Band Gap / blockers / comparison keep working unchanged.
    """
    criteria = {
        "Task Response": _coerce_band(data.get("task_response")),
        "Coherence & Cohesion": _coerce_band(data.get("coherence_cohesion")),
        "Lexical Resource": _coerce_band(data.get("lexical_resource")),
        "Grammatical Range & Accuracy": _coerce_band(data.get("grammatical_range_accuracy")),
    }
    scored = [v for v in criteria.values() if v > 0]
    overall = _coerce_band(data.get("overall_band")) or (
        _round_half(sum(scored) / len(scored)) if scored else 0.0
    )
    if overall == 0 and not scored:
        raise ValueError("Gemini returned no usable band scores")

    strengths = _str_list(data.get("strengths"))
    weaknesses = _str_list(data.get("weaknesses"))
    actions = _str_list(data.get("improvement_actions"))
    mistakes = _parse_mistakes(data.get("mistakes"))

    return Feedback(
        band=overall,
        criteria=criteria,
        summary=_build_summary(overall, strengths, weaknesses),
        suggestions=actions,  # keep `suggestions` populated for backward compat
        mistakes=mistakes,
        strengths=strengths,
        weaknesses=weaknesses,
        actions=actions,
    )


# ── Speaking helpers (existing schema, unchanged) ────────────────────────────

def _to_feedback_speaking(data: dict) -> Feedback:
    criteria = {k: float(v) for k, v in data.get("criteria", {}).items()}
    band = float(data.get("band") or (sum(criteria.values()) / len(criteria) if criteria else 0))
    return Feedback(
        band=band,
        criteria=criteria,
        summary=str(data.get("summary", "")),
        suggestions=[str(s) for s in data.get("suggestions", [])],
    )


# ── Providers ────────────────────────────────────────────────────────────────

class GeminiWritingGrader(WritingGrader):
    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        word_count = len([w for w in text.split() if w.strip()])
        user = build_writing_user_prompt(
            task_type=task_type,
            prompt=prompt,
            text=text,
            min_words=min_words,
            word_count=word_count,
        )
        try:
            raw = _generate([user], WRITING_SYSTEM, max_output_tokens=2048)
            data = _parse(raw)
            return _validate_writing(data)
        except Exception as exc:  # noqa: BLE001 — fall back, never 500 the endpoint
            logger.warning(
                "Gemini writing grading failed (%s: %s) — falling back to mock provider.",
                type(exc).__name__,
                exc,
            )
            return MockWritingGrader().grade(
                task_type=task_type, prompt=prompt, text=text, min_words=min_words
            )


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

        prompt = build_speaking_user_prompt(part=part, questions=questions)
        try:
            path = Path(audio_path)
            mime = _AUDIO_MIME.get(path.suffix.lower(), "audio/webm")
            audio_bytes = path.read_bytes()
            contents = [
                types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                prompt,
            ]
            raw = _generate(contents, SPEAKING_SYSTEM, max_output_tokens=1024)
            return _to_feedback_speaking(_parse(raw))
        except Exception as exc:  # noqa: BLE001 — fall back, never 500 the endpoint
            logger.warning(
                "Gemini speaking grading failed (%s: %s) — falling back to mock provider.",
                type(exc).__name__,
                exc,
            )
            return MockSpeakingGrader().grade(
                part=part, questions=questions, audio_path=audio_path, transcript=transcript
            )
