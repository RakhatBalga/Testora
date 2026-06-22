"""Real Claude-based graders.

Fully implemented but only used when AI_PROVIDER=claude and a key is set
(see factory.py). The `anthropic` package is imported lazily so the app runs
without it installed while we're on the mock provider.
"""

import json

from app.core.config import settings
from app.services.ai.base import Feedback, WritingGrader, SpeakingGrader

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


def _client():
    from anthropic import Anthropic  # lazy import

    return Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _ask_json(system: str, user: str) -> dict:
    """Call Claude and parse a single JSON object from the reply."""
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = msg.content[0].text.strip()
    # Strip markdown fences if the model wrapped the JSON.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    return json.loads(raw)


def _to_feedback(data: dict) -> Feedback:
    criteria = {k: float(v) for k, v in data.get("criteria", {}).items()}
    band = float(data.get("band") or (sum(criteria.values()) / len(criteria) if criteria else 0))
    return Feedback(
        band=band,
        criteria=criteria,
        summary=str(data.get("summary", "")),
        suggestions=[str(s) for s in data.get("suggestions", [])],
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
    "You are an experienced IELTS examiner. Grade the candidate's spoken response "
    "(given as a transcript) using the official IELTS band descriptors (0-9, "
    "half-bands allowed) for four criteria: Fluency & Coherence, Lexical Resource, "
    "Grammatical Range & Accuracy, Pronunciation. Respond ONLY with a JSON object of "
    'the form: {"band": number, "criteria": {"Fluency & Coherence": number, '
    '"Lexical Resource": number, "Grammatical Range & Accuracy": number, '
    '"Pronunciation": number}, "summary": string, "suggestions": [string, ...]}.'
)


class ClaudeWritingGrader(WritingGrader):
    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        user = (
            f"IELTS Writing Task {task_type}. Minimum words: {min_words}.\n\n"
            f"PROMPT:\n{prompt}\n\nCANDIDATE RESPONSE:\n{text}"
        )
        return _to_feedback(_ask_json(_WRITING_SYSTEM, user))


class ClaudeSpeakingGrader(SpeakingGrader):
    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback:
        if not transcript:
            return Feedback(
                band=0.0,
                criteria={},
                summary=(
                    "No transcript available. Run speech-to-text on the recording "
                    "before grading."
                ),
                suggestions=["Transcription step required."],
            )
        joined = "\n".join(f"- {q}" for q in questions)
        user = (
            f"IELTS Speaking Part {part}.\n\nQUESTIONS:\n{joined}\n\n"
            f"CANDIDATE TRANSCRIPT:\n{transcript}"
        )
        return _to_feedback(_ask_json(_SPEAKING_SYSTEM, user))
