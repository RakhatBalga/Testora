from app.core.config import settings
from app.services.ai.base import WritingGrader, SpeakingGrader
from app.services.ai.mock import MockWritingGrader, MockSpeakingGrader


def _provider() -> str:
    p = settings.AI_PROVIDER.lower()
    if p == "claude" and settings.ANTHROPIC_API_KEY:
        return "claude"
    if p == "gemini" and settings.GEMINI_API_KEY:
        return "gemini"
    return "mock"


def get_writing_grader() -> WritingGrader:
    provider = _provider()
    if provider == "claude":
        from app.services.ai.claude import ClaudeWritingGrader

        return ClaudeWritingGrader()
    if provider == "gemini":
        from app.services.ai.gemini import GeminiWritingGrader

        return GeminiWritingGrader()
    return MockWritingGrader()


def get_speaking_grader() -> SpeakingGrader:
    provider = _provider()
    if provider == "claude":
        from app.services.ai.claude import ClaudeSpeakingGrader

        return ClaudeSpeakingGrader()
    if provider == "gemini":
        from app.services.ai.gemini import GeminiSpeakingGrader

        return GeminiSpeakingGrader()
    return MockSpeakingGrader()
