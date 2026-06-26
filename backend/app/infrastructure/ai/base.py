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
    # Per-criterion examiner justification (criterion name -> 1-2 sentence note).
    criteria_notes: dict[str, str] = field(default_factory=dict)
    # Coaching extras (populated by the two-stage Writing engine; empty otherwise).
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    roadmap: list[dict] = field(default_factory=list)  # [{target_band, actions[]}]
    # True when grading could not be completed (AI error/timeout/malformed
    # output). The caller must NOT persist this as a real Band-0 grade.
    error: bool = False

    def to_dict(self) -> dict:
        # Mistakes are persisted separately (mistakes table), not in the stored
        # feedback JSON. The extra coaching keys are additive and backward
        # compatible — older consumers read band/criteria/summary/suggestions.
        data = {
            "band": self.band,
            "criteria": self.criteria,
            "summary": self.summary,
            "suggestions": self.suggestions,
        }
        if self.criteria_notes:
            data["criteria_notes"] = self.criteria_notes
        if self.strengths:
            data["strengths"] = self.strengths
        if self.weaknesses:
            data["weaknesses"] = self.weaknesses
        if self.actions:
            data["actions"] = self.actions
        if self.roadmap:
            data["roadmap"] = self.roadmap
        return data


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
