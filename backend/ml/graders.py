"""Isolated adapter between the E1 tooling and the app's grader factory.

Contract: `app.infrastructure.ai.factory.get_writing_grader(provider=...)` with
providers mock | gemini | claude | qwen. A named provider that is unknown or
missing its settings raises ProviderUnavailable here (the factory raises
ProviderNotConfigured), so an experiment can never silently measure the mock
grader under another provider's label.
"""
import hashlib
import importlib.util
import inspect
from pathlib import Path
from typing import Callable

_REGISTRY: dict[str, Callable[[], object]] = {}


def register_grader(name: str, builder: Callable[[], object]) -> None:
    """Register a custom grader (used by tests and offline experiments)."""
    _REGISTRY[name] = builder


def unregister_grader(name: str) -> None:
    _REGISTRY.pop(name, None)


class ProviderUnavailable(RuntimeError):
    pass


def make_grader(provider: str):
    if provider in _REGISTRY:
        return _REGISTRY[provider]()
    from app.infrastructure.ai import factory

    try:
        return factory.get_writing_grader(provider=provider)
    except factory.ProviderNotConfigured as exc:
        raise ProviderUnavailable(f"provider {provider!r} is not usable here: {exc}") from exc


def model_name(provider: str, grader=None) -> str:
    """Best-effort model identifier recorded with every cached response."""
    if grader is not None and getattr(grader, "model_name", None):
        return str(grader.model_name)
    if provider in ("mock", "rules") or provider in _REGISTRY:
        return "rules-v1" if provider == "mock" else provider
    try:
        from app.infrastructure.config import settings
    except Exception:  # pragma: no cover - app not importable
        return "unknown"
    attr = {"gemini": "GEMINI_MODEL", "qwen": "QWEN_MODEL", "claude": "ANTHROPIC_MODEL"}.get(provider)
    return str(getattr(settings, attr, None) or "unknown") if attr else "unknown"


def prompt_version(override: str | None = None) -> str:
    """Short hash of the examiner prompt + schema sources (frozen-protocol key)."""
    if override:
        return override
    digest = hashlib.sha256()
    found = False
    for module in ("app.infrastructure.ai.prompts", "app.infrastructure.ai.schemas"):
        try:
            spec = importlib.util.find_spec(module)
        except Exception:  # pragma: no cover
            spec = None
        if spec and spec.origin and Path(spec.origin).is_file():
            digest.update(Path(spec.origin).read_bytes())
            found = True
    return digest.hexdigest()[:12] if found else "unknown"


def grade_call(grader, *, task_type: int, prompt: str, text: str, min_words: int, seed: int | None):
    """Call grader.grade, passing `seed` only if the grader accepts it."""
    kwargs = dict(task_type=task_type, prompt=prompt, text=text, min_words=min_words)
    if seed is not None and "seed" in inspect.signature(grader.grade).parameters:
        kwargs["seed"] = seed
    return grader.grade(**kwargs)
