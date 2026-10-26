from abc import ABC, abstractmethod

# Feedback/MistakeItem live in the domain now; re-exported so existing
# `from app.infrastructure.ai.base import Feedback` imports keep working.
from app.domain.grading import Feedback, MistakeItem  # noqa: F401


class WritingGrader(ABC):
    @abstractmethod
    def grade(
        self,
        *,
        task_type: int,
        prompt: str,
        text: str,
        min_words: int,
    ) -> Feedback: ...

    def improve(self, *, task_type: int, prompt: str, text: str) -> str | None:
        """Rewrite the essay as a higher-band "Better Version" (plain text).

        Optional capability: providers without an LLM (e.g. the mock grader)
        return None, and the UI falls back to its deterministic diff engine.
        """
        return None


class SpeakingGrader(ABC):
    @abstractmethod
    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback: ...
