from app.infrastructure.config import settings
from app.infrastructure.ai.base import WritingGrader, SpeakingGrader
from app.infrastructure.ai.mock import MockWritingGrader, MockSpeakingGrader


def _provider() -> str:
    p = settings.AI_PROVIDER.lower()
    if p == "claude" and settings.ANTHROPIC_API_KEY:
        return "claude"
    if p == "gemini" and settings.GEMINI_API_KEY:
        return "gemini"
    return "mock"


def effective_provider() -> str:
    """The provider that will actually grade, after key-presence fallback.

    Equals "mock" whenever a real provider is selected but its API key is
    missing. Startup validation uses this to refuse a production launch on the
    mock grader.
    """
    return _provider()


def get_writing_grader() -> WritingGrader:
    provider = _provider()
    if provider == "claude":
        from app.infrastructure.ai.claude import ClaudeWritingGrader

        return ClaudeWritingGrader()
    if provider == "gemini":
        from app.infrastructure.ai.gemini import GeminiWritingGrader

        return GeminiWritingGrader()
    return MockWritingGrader()


def get_speaking_grader() -> SpeakingGrader:
    provider = _provider()
    if provider == "claude":
        from app.infrastructure.ai.claude import ClaudeSpeakingGrader

        return ClaudeSpeakingGrader()
    if provider == "gemini":
        from app.infrastructure.ai.gemini import GeminiSpeakingGrader

        return GeminiSpeakingGrader()
    return MockSpeakingGrader()
