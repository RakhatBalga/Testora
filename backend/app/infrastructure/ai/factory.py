from app.infrastructure.config import settings
from app.infrastructure.ai.base import WritingGrader, SpeakingGrader
from app.infrastructure.ai.mock import MockWritingGrader, MockSpeakingGrader
from app.infrastructure.ai.vocab import VocabularyCoach, MockVocabularyCoach

PROVIDERS = ("mock", "gemini", "claude", "qwen")


class ProviderNotConfigured(ValueError):
    """An explicitly requested provider is unknown or missing its settings."""


class SeedNotSupported(ValueError):
    """A sampling seed was requested for a provider that cannot apply one."""


# Providers whose API takes a sampling seed. Claude's Messages API has none and
# the mock grader is deterministic rules.
SEEDED_PROVIDERS = ("gemini", "qwen")


def provider_configured(provider: str) -> bool:
    """True when the provider has the settings it needs to make real calls."""
    p = provider.lower().strip()
    if p == "mock":
        return True
    if p == "gemini":
        return bool(settings.GEMINI_API_KEY)
    if p == "claude":
        return bool(settings.ANTHROPIC_API_KEY)
    if p == "qwen":
        return bool(settings.QWEN_BASE_URL.strip() and settings.QWEN_MODEL.strip())
    return False


def _provider(requested: str | None = None) -> str:
    """Resolve the provider.

    `requested=None` uses AI_PROVIDER and silently falls back to "mock" when
    it is unknown or unconfigured (the production startup check refuses that).
    An explicit `requested` provider never falls back: an experiment asking
    for "qwen" must not quietly get mock grades.
    """
    if requested is not None:
        p = requested.lower().strip()
        if p not in PROVIDERS:
            raise ProviderNotConfigured(f"unknown AI provider {requested!r}; expected one of {PROVIDERS}")
        if not provider_configured(p):
            raise ProviderNotConfigured(f"AI provider {p!r} is not configured (missing key/URL/model)")
        return p
    p = settings.AI_PROVIDER.lower().strip()
    if p in PROVIDERS and provider_configured(p):
        return p
    return "mock"


def effective_provider() -> str:
    """The provider that will actually grade, after configuration fallback.

    Equals "mock" whenever a real provider is selected but its key (or, for
    qwen, QWEN_BASE_URL/QWEN_MODEL) is missing. Startup validation uses this
    to refuse a production launch on the mock grader.
    """
    return _provider()


def get_writing_grader(provider: str | None = None, *, seed: int | None = None) -> WritingGrader:
    """`seed=None` (every production caller) keeps the provider default, the fixed
    engine GRADING_SEED. An explicit seed is sent with every request of the
    returned grader; a provider that cannot take one raises SeedNotSupported
    rather than ignoring it."""
    p = _provider(provider)
    if seed is not None and p not in SEEDED_PROVIDERS:
        raise SeedNotSupported(f"AI provider {p!r} does not take a sampling seed")
    seeded = {} if seed is None else {"seed": seed}
    if p == "claude":
        from app.infrastructure.ai.claude import ClaudeWritingGrader

        return ClaudeWritingGrader()
    if p == "gemini":
        from app.infrastructure.ai.gemini import GeminiWritingGrader

        return GeminiWritingGrader(**seeded)
    if p == "qwen":
        from app.infrastructure.ai.qwen import QwenWritingGrader

        return QwenWritingGrader(**seeded)
    return MockWritingGrader()


def get_speaking_grader(provider: str | None = None) -> SpeakingGrader:
    p = _provider(provider)
    if p == "claude":
        from app.infrastructure.ai.claude import ClaudeSpeakingGrader

        return ClaudeSpeakingGrader()
    if p == "gemini":
        from app.infrastructure.ai.gemini import GeminiSpeakingGrader

        return GeminiSpeakingGrader()
    if p == "qwen":
        from app.infrastructure.ai.qwen import QwenSpeakingGrader

        return QwenSpeakingGrader()
    return MockSpeakingGrader()


def get_vocabulary_coach(provider: str | None = None) -> VocabularyCoach:
    """Word enrichment + quiz generation. Gemini and Qwen have real coaches;
    mock and the experimental claude provider use the deterministic offline
    coach — enrichment degrades honestly, cloze quizzes still work."""
    p = _provider(provider)
    if p == "gemini":
        from app.infrastructure.ai.gemini import GeminiVocabularyCoach

        return GeminiVocabularyCoach()
    if p == "qwen":
        from app.infrastructure.ai.qwen import QwenVocabularyCoach

        return QwenVocabularyCoach()
    return MockVocabularyCoach()
