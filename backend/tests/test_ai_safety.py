"""Provider fallback + production fail-fast guard."""
import importlib

import pytest

from app.infrastructure.config import settings
from app.infrastructure.ai import factory


def _reload_factory():
    importlib.reload(factory)
    return factory


def test_effective_provider_falls_back_to_mock_without_key(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert _reload_factory().effective_provider() == "mock"


def test_effective_provider_gemini_with_key(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "key-present")
    assert _reload_factory().effective_provider() == "gemini"


def test_production_mock_is_rejected(monkeypatch):
    """The startup guard must raise when production resolves to the mock grader."""
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    from app import main

    with pytest.raises(RuntimeError, match="mock grader"):
        main._validate_ai_configuration()


def test_development_mock_is_allowed(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    from app import main

    main._validate_ai_configuration()  # must not raise


@pytest.mark.parametrize(
    "weak",
    ["", "CHANGE_ME", "changeme", "secret", "short", "mysecretkey123", "MySecretKey123"],
)
def test_production_weak_secret_key_is_rejected(monkeypatch, weak):
    """The startup guard must reject a missing/placeholder/short/leaked SECRET_KEY.

    "mysecretkey123" leaked in this repo's git history, so it is permanently
    burned and must be rejected regardless of casing or length.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", weak)
    from app import main

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        main._validate_security_configuration()


def test_production_strong_secret_key_is_allowed(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "a" * 64)
    from app import main

    main._validate_security_configuration()  # must not raise


def test_development_weak_secret_key_is_allowed(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "SECRET_KEY", "CHANGE_ME")
    from app import main

    main._validate_security_configuration()  # must not raise


# ------------------------------ qwen + overrides ----------------------------

def test_effective_provider_qwen_requires_url_and_model(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "QWEN_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(settings, "QWEN_MODEL", "")
    assert _reload_factory().effective_provider() == "mock"
    monkeypatch.setattr(settings, "QWEN_MODEL", "qwen3:14b")
    assert _reload_factory().effective_provider() == "qwen"


def test_factory_returns_qwen_graders(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "QWEN_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(settings, "QWEN_MODEL", "qwen3:14b")
    f = _reload_factory()
    from app.infrastructure.ai import qwen

    assert isinstance(f.get_writing_grader(), qwen.QwenWritingGrader)
    assert isinstance(f.get_speaking_grader(), qwen.QwenSpeakingGrader)
    assert isinstance(f.get_vocabulary_coach(), qwen.QwenVocabularyCoach)


def test_explicit_provider_overrides_settings(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "key-present")
    f = _reload_factory()
    from app.infrastructure.ai import gemini, mock

    assert isinstance(f.get_writing_grader(provider="gemini"), gemini.GeminiWritingGrader)
    assert isinstance(f.get_writing_grader(provider="mock"), mock.MockWritingGrader)
    assert isinstance(f.get_writing_grader(), mock.MockWritingGrader)


@pytest.mark.parametrize("provider", ["qwen", "claude", "openai"])
def test_explicit_unconfigured_or_unknown_provider_never_falls_back_to_mock(monkeypatch, provider):
    monkeypatch.setattr(settings, "QWEN_BASE_URL", "")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    f = _reload_factory()
    with pytest.raises(f.ProviderNotConfigured):
        f.get_writing_grader(provider=provider)


def test_production_qwen_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AI_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "QWEN_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setattr(settings, "QWEN_MODEL", "qwen3-14b")
    _reload_factory()
    from app import main

    monkeypatch.setattr(main, "effective_provider", factory.effective_provider)
    main._validate_ai_configuration()  # must not raise
