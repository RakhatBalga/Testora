from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MistakeItem:
    """An atomic mistake extracted during grading. Persisted to the `mistakes`
    table so analytics can aggregate weaknesses across attempts (no AI at read time)."""

    category: str          # e.g. grammar | vocabulary | coherence | task_response | fluency ...
    subskill: str | None   # e.g. articles | word_repetition | paragraphing | answer_length
    severity: int = 1      # 1 (minor) .. 3 (band-limiting)
    snippet: str | None = None
    correction: str | None = None
    explanation: str | None = None


@dataclass
class Feedback:
    """Result of grading a Writing or Speaking submission."""

    band: float
    criteria: dict[str, float]  # criterion name -> band (0-9)
    summary: str
    suggestions: list[str] = field(default_factory=list)
    mistakes: list[MistakeItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        # Mistakes are persisted separately (mistakes table), not in the stored
        # feedback JSON, so the submission feedback shape stays stable.
        return {
            "band": self.band,
            "criteria": self.criteria,
            "summary": self.summary,
            "suggestions": self.suggestions,
        }


class WritingGrader(ABC):
    @abstractmethod
    def grade(
        self,
        *,
        task_type: int,
        prompt: str,
        text: str,
        min_words: int,
    ) -> Feedback:
        ...


class SpeakingGrader(ABC):
    @abstractmethod
    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback:
        ...
