"""AI capabilities the use cases need, as interfaces.

The use cases call `get_writing_grader()` and its siblings; which provider
answers (mock, Gemini, Qwen, ...) is decided outside the application layer and
registered once with `configure` (see `app/bootstrap.py`).
"""

from typing import Any, Callable, Protocol

from app.domain.grading import Feedback


class WritingGrader(Protocol):
    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback: ...

    def improve(self, *, task_type: int, prompt: str, text: str) -> str | None: ...


class SpeakingGrader(Protocol):
    def grade(self, *, part: int, questions: list[str], audio_path: str, transcript: str | None) -> Feedback: ...


class VocabularyCoach(Protocol):
    """Results expose `error` and `to_dict()`; a quiz also lists `questions`."""

    def enrich_word(self, *, word: str, context: str | None, native_language: str | None) -> Any: ...

    def generate_quiz(self, *, words: list[dict], native_language: str | None, num_questions: int) -> Any: ...


_providers: dict[str, Callable[[], Any]] = {}


def configure(
    *,
    writing_grader: Callable[[], WritingGrader],
    speaking_grader: Callable[[], SpeakingGrader],
    vocabulary_coach: Callable[[], VocabularyCoach],
) -> None:
    """Register the factories that build each capability (called at startup)."""
    _providers.update(writing=writing_grader, speaking=speaking_grader, vocabulary=vocabulary_coach)


def _resolve(name: str):
    try:
        factory = _providers[name]
    except KeyError:
        raise RuntimeError("AI providers are not configured; import app.bootstrap before using them") from None
    return factory()


def get_writing_grader() -> WritingGrader:
    return _resolve("writing")


def get_speaking_grader() -> SpeakingGrader:
    return _resolve("speaking")


def get_vocabulary_coach() -> VocabularyCoach:
    return _resolve("vocabulary")
