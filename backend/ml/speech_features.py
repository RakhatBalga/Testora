"""ASR-derived fluency proxies, not pronunciation or IELTS grades."""

from statistics import mean
from pydantic import Field, model_validator
from ml.data import Record
from ml.metrics import words

FEATURE_VERSION = "fluency.v1"
FEATURE_NAMES = (
    "word_count",
    "words_per_minute",
    "articulation_words_per_minute",
    "pause_count",
    "interword_pause_ratio",
    "mean_pause_seconds",
    "filler_ratio",
    "immediate_repeat_ratio",
    "repair_marker_count",
    "mean_asr_confidence",
)


class TimedWord(Record):
    text: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    probability: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def interval(self):
        if self.end < self.start:
            raise ValueError("Word end precedes start")
        return self


class Transcript(Record):
    text: str
    duration_seconds: float = Field(gt=0)
    words: list[TimedWord]

    @model_validator(mode="after")
    def timeline(self):
        previous_end = 0.0
        for word in self.words:
            if word.start < previous_end or word.end > self.duration_seconds:
                raise ValueError("Word timestamps overlap, are unordered, or exceed audio duration")
            previous_end = word.end
        return self


def extract_features(transcript: Transcript, pause_threshold: float = 0.25) -> dict[str, float | None]:
    if not 0 < pause_threshold < float("inf"):
        raise ValueError("Pause threshold must be positive and finite")
    tokens = words(transcript.text)
    count = len(tokens)
    timed = transcript.words
    gaps = [b.start - a.end for a, b in zip(timed, timed[1:])]
    pauses = [gap for gap in gaps if gap >= pause_threshold]
    articulation = sum(w.end - w.start for w in timed)
    timed_count = sum(len(words(w.text)) for w in timed)
    confidence = [w.probability for w in timed if w.probability is not None]
    return {
        "word_count": float(count),
        "words_per_minute": count * 60 / transcript.duration_seconds,
        "articulation_words_per_minute": timed_count * 60 / articulation if articulation else None,
        "pause_count": float(len(pauses)) if timed else None,
        "interword_pause_ratio": sum(pauses) / transcript.duration_seconds if timed else None,
        "mean_pause_seconds": mean(pauses) if pauses else (0.0 if timed else None),
        "filler_ratio": sum(t in {"um", "uh", "erm", "er", "hmm"} for t in tokens) / count if count else 0.0,
        "immediate_repeat_ratio": sum(a == b for a, b in zip(tokens, tokens[1:])) / max(1, count - 1),
        "repair_marker_count": float(sum((a, b) == ("i", "mean") for a, b in zip(tokens, tokens[1:]))),
        "mean_asr_confidence": mean(confidence) if confidence else None,
    }
