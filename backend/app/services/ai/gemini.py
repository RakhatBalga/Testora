"""Google Gemini-based graders.

Used when AI_PROVIDER=gemini and GEMINI_API_KEY is set (see factory.py).
The `google-genai` package is imported lazily so the app runs without it
installed while on the mock provider.

Gemini is multimodal, so the Speaking grader sends the recorded audio file
directly to the model — no separate speech-to-text step is required.
"""

import json
from pathlib import Path

from app.core.config import settings
from app.services.ai.base import Feedback, WritingGrader, SpeakingGrader

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


def _config(system: str):
    from google.genai import types

    return types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        max_output_tokens=1024,
        temperature=0.3,
    )


def _generate(contents, system: str) -> str:
    """Call Gemini with a fresh client, retrying once on transient failures.

    Each attempt builds a new client because the SDK's internal retry reuses a
    closed httpx connection; a fresh client sidesteps that.
    """
    last_exc: Exception | None = None
    for _ in range(2):
        try:
            resp = _client().models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=_config(system),
            )
            return resp.text
        except Exception as exc:  # noqa: BLE001 — retried, then surfaced
            last_exc = exc
    raise last_exc  # type: ignore[misc]


def _parse(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    return json.loads(raw)


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
    """Returned when the AI call fails, so the submission is still saved."""
    return Feedback(
        band=0.0,
        criteria={},
        summary=f"Automatic grading could not be completed: {message}",
        suggestions=["Try submitting again, or check the AI configuration."],
    )


_WRITING_SYSTEM = (
    "You are an experienced IELTS examiner. Grade the candidate's writing using the "
    "official IELTS band descriptors (0-9, half-bands allowed) for four criteria: "
    "Task Achievement, Coherence & Cohesion, Lexical Resource, "
    "Grammatical Range & Accuracy. Respond ONLY with a JSON object of the form: "
    '{"band": number, "criteria": {"Task Achievement": number, '
    '"Coherence & Cohesion": number, "Lexical Resource": number, '
    '"Grammatical Range & Accuracy": number}, "summary": string, '
    '"suggestions": [string, ...]}.'
)

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


class GeminiWritingGrader(WritingGrader):
    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        user = (
            f"IELTS Writing Task {task_type}. Minimum words: {min_words}.\n\n"
            f"PROMPT:\n{prompt}\n\nCANDIDATE RESPONSE:\n{text}"
        )
        try:
            return _to_feedback(_parse(_generate([user], _WRITING_SYSTEM)))
        except Exception as exc:  # noqa: BLE001 — never 500 the submit endpoint
            return _error_feedback(str(exc))


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
            return _to_feedback(_parse(_generate(contents, _SPEAKING_SYSTEM)))
        except Exception as exc:  # noqa: BLE001
            return _error_feedback(str(exc))
