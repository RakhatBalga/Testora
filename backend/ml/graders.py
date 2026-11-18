"""Isolated adapter between the E1 tooling and the app's grader factory.

Contract: `app.infrastructure.ai.factory.get_writing_grader(provider=...)` with
providers mock | gemini | claude | qwen. A named provider that is unknown or
missing its settings raises ProviderUnavailable here (the factory raises
ProviderNotConfigured), so an experiment can never silently measure the mock
grader under another provider's label.

`experiment_run` is the single entry point for a measured run. It applies the
requested examiner prompt version and model to the app settings for the duration
of the run, refuses any input it cannot apply, and returns the values that are
really in effect (model, prompt version, seed). Those are what the collector
writes into the cache key and what the report prints.
"""

import hashlib
import importlib.util
import inspect
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

_REGISTRY: dict[str, Callable[[], object]] = {}

# Providers graded by the shared engine (app.infrastructure.ai.engine): they use
# the versioned examiner prompt. The mock grader is rule-based and has no prompt.
ENGINE_PROVIDERS = ("gemini", "claude", "qwen")
_MODEL_SETTING = {"gemini": "GEMINI_MODEL", "qwen": "QWEN_MODEL"}


def register_grader(name: str, builder: Callable[[], object]) -> None:
    """Register a custom grader (used by tests and offline experiments)."""
    _REGISTRY[name] = builder


def unregister_grader(name: str) -> None:
    _REGISTRY.pop(name, None)


class ProviderUnavailable(RuntimeError):
    pass


class RunInputError(ValueError):
    """A requested prompt version, model or seed cannot be applied to the run."""


def make_grader(provider: str, seed: int | None = None):
    """Build the grader. `seed` goes to the factory, which hands it to the
    provider's transport or refuses it (SeedNotSupported -> RunInputError)."""
    if provider in _REGISTRY:
        return _REGISTRY[provider]()
    from app.infrastructure.ai import factory

    try:
        return factory.get_writing_grader(provider=provider, seed=seed)
    except factory.SeedNotSupported as exc:
        raise RunInputError(f"{exc}; {seed} cannot be applied") from None
    except factory.ProviderNotConfigured as exc:
        raise ProviderUnavailable(f"provider {provider!r} is not usable here: {exc}") from exc


def _transport(grader):
    return getattr(getattr(grader, "engine", None), "transport", None)


def model_name(provider: str, grader=None) -> str:
    """The model that grades, read from the grader itself whenever possible."""
    if grader is not None:
        if getattr(grader, "model_name", None):
            return str(grader.model_name)
        transport = _transport(grader)
        if transport is not None:
            return str(transport.model_for("examiner"))
    if provider in _REGISTRY:
        return provider
    if provider == "mock":
        from app.infrastructure.ai.mock import MOCK_MODEL

        return MOCK_MODEL
    if provider == "claude":
        from app.infrastructure.ai.claude import MODEL  # fixed in code, no setting

        return MODEL
    if provider in _MODEL_SETTING:
        from app.infrastructure.config import settings

        return str(getattr(settings, _MODEL_SETTING[provider], None) or "unknown")
    return "unknown"


def source_hash() -> str:
    """Short hash of the prompt + schema sources; moves on any edit to either file."""
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


def examiner_version(requested: str | None = None) -> str:
    """Validated examiner prompt version (v1 | v2); None reads the app setting."""
    from app.infrastructure.ai import prompts

    return prompts.active_examiner_version(requested)


def prompt_version(provider: str, examiner: str | None = None) -> str:
    """Prompt version used as the cache key.

    Engine providers: `examiner-<v>+<prompt fingerprint>+src.<source hash>`. The
    first two parts are exactly what the engine stamps on every Feedback, so the
    v1 and v2 examiner prompts can never share a key. The mock grader and
    registered graders do not use the examiner prompt: their key is the mock
    method version (or `custom`) plus the source hash.
    """
    src = f"src.{source_hash()}"
    if provider in _REGISTRY:
        return f"custom+{src}"
    if provider == "mock":
        from app.infrastructure.ai.mock import MOCK_METHOD_VERSION

        return f"{MOCK_METHOD_VERSION}+{src}"
    from app.infrastructure.ai import prompts

    return f"{prompts.prompt_version(examiner_version(examiner))}+{src}"


def accepts_seed(grader) -> bool:
    return "seed" in inspect.signature(grader.grade).parameters


def transport_seed(grader) -> int | None:
    """The seed the grader's transport sends with its requests; None when the
    transport has no seed (Claude) or the grader has no transport (mock)."""
    return getattr(_transport(grader), "seed", None)


def seed_for_run(base: int | None, run: int) -> int | None:
    """Seed of run `run`: base + run, so repeated runs use distinct seeds and run 0
    uses the base seed. None stays None (provider without a seed)."""
    return None if base is None else base + run


@dataclass(frozen=True)
class RunSpec:
    """What a run really uses. Every field is effective, never a free label."""

    grader: object
    provider: str
    model: str
    examiner_version: str | None  # v1 | v2 for engine providers, else None
    prompt_version: str
    seed: int | None  # base seed (run 0); run r sends seed + r. None = no seed is applied

    def collect_kwargs(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "examiner_version": self.examiner_version,
            "seed": self.seed,
        }


@contextmanager
def experiment_run(
    provider: str,
    *,
    examiner: str | None = None,
    model: str | None = None,
    seed: int | None = None,
) -> Iterator[RunSpec]:
    """Build a grader with the requested inputs applied; grade inside the block.

    `seed` is the base seed. Gemini and Qwen take it through the grader factory
    (default: the engine's GRADING_SEED, which is what production sends); Claude
    and the mock grader cannot take a seed and refuse one.

    Raises RunInputError for an input that would not be applied, so a run can never
    be labelled with a prompt version, model or seed it did not use.
    """
    engine = provider in ENGINE_PROVIDERS and provider not in _REGISTRY
    overrides: dict[str, object] = {}
    if engine:
        if examiner is None:
            raise RunInputError(
                f"provider {provider!r} needs an explicit examiner prompt version (v1 or v2): "
                "production pins v1 while the code default is v2, so the run must say which one it measures"
            )
        try:
            examiner = examiner_version(examiner)
        except ValueError as exc:
            raise RunInputError(str(exc)) from None
        overrides["EXAMINER_PROMPT_VERSION"] = examiner
        if model is not None:
            if provider in _MODEL_SETTING:
                overrides[_MODEL_SETTING[provider]] = model
            elif model != model_name(provider):
                raise RunInputError(
                    f"the {provider} model is fixed in code ({model_name(provider)}); {model!r} cannot be applied"
                )
    elif examiner is not None:
        raise RunInputError(f"provider {provider!r} does not use the examiner prompt; drop the examiner version")

    from app.infrastructure.config import settings

    saved = {key: getattr(settings, key) for key in overrides}
    for key, value in overrides.items():
        setattr(settings, key, value)
    try:
        grader = make_grader(provider, seed if engine else None)
        effective_model = model_name(provider, grader)
        if model is not None and model != effective_model:
            raise RunInputError(
                f"model {model!r} cannot be applied to {provider!r} (it grades with {effective_model!r})"
            )
        if engine:
            effective_seed = transport_seed(grader)  # read back from the transport that sends it
            if seed is not None and effective_seed != seed:
                raise RunInputError(f"seed {seed} did not reach the {provider} transport ({effective_seed})")
        elif seed is not None and not accepts_seed(grader):
            raise RunInputError(f"the {provider!r} grader takes no seed; {seed} cannot be applied")
        else:
            effective_seed = seed
        yield RunSpec(
            grader=grader,
            provider=provider,
            model=effective_model,
            examiner_version=examiner if engine else None,
            prompt_version=prompt_version(provider, examiner if engine else None),
            seed=effective_seed,
        )
    finally:
        for key, value in saved.items():
            setattr(settings, key, value)


def provenance_mismatch(feedback, *, model: str, prompt_version: str) -> str | None:
    """Compare what the grader stamped on its result with what the run records.

    Graders that stamp nothing (plain test doubles) are not checked.
    """
    reported_model = getattr(feedback, "model", "") or ""
    if reported_model and reported_model != model:
        return f"grader reported model {reported_model!r}, run records {model!r}"
    reported_version = getattr(feedback, "prompt_version", "") or ""
    if reported_version and prompt_version.split("+src.")[0] != reported_version:
        return f"grader reported prompt {reported_version!r}, run records {prompt_version!r}"
    return None


def grade_call(grader, *, task_type: int, prompt: str, text: str, min_words: int, seed: int | None):
    """Grade once with `seed` really applied, or refuse.

    The seed goes to `grade(seed=...)` when the grader accepts it, else to the
    grader's transport (Gemini, Qwen), which sends it with the request. A seed
    that can go nowhere raises RunInputError: a record never carries a seed that
    was not used.
    """
    kwargs = dict(task_type=task_type, prompt=prompt, text=text, min_words=min_words)
    if seed is not None:
        transport = _transport(grader)
        if accepts_seed(grader):
            kwargs["seed"] = seed
        elif hasattr(transport, "seed"):
            transport.seed = seed
        else:
            raise RunInputError(f"this grader takes no seed; {seed} cannot be applied")
    return grader.grade(**kwargs)
