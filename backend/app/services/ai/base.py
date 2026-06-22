from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field


@dataclass
class Feedback:
    """Result of grading a Writing or Speaking submission."""

    band: float
    criteria: dict[str, float]  # criterion name -> band (0-9)
    summary: str
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


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
