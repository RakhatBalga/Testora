"""Provider fallback + production fail-fast guard."""
import importlib

import pytest

from app.core.config import settings
from app.services.ai import factory


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
