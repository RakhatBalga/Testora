"""The sampling seed is an input of grader construction.

Default = the fixed engine GRADING_SEED (what production sends). An explicit
seed reaches the provider request; providers without a seed refuse one.
"""

import json

import httpx
import pytest

from app.infrastructure.ai import factory, gemini, qwen
from app.infrastructure.ai.engine import GRADING_SEED
from app.infrastructure.ai.openai_compat import OpenAICompatClient, reset_json_schema_cache
from app.infrastructure.config import settings

ESSAY = (
    "Some people believe governments should spend money on public transport rather than "
    "new roads. In my view, buses and trains are the better investment for most cities. "
    "Firstly, public transport moves many people using little space, so traffic falls. "
    "Secondly, it reduces pollution because fewer private cars are used every day. "
    "However, roads are still needed in rural areas where trains do not run. "
    "Overall, public transport should receive most of the money in growing cities."
)
EXAMINER = {
    "task_response": {"band": 6.5, "justification": "clear position"},
    "coherence_cohesion": {"band": 6.5, "justification": "logical"},
    "lexical_resource": {"band": 7.0, "justification": "good range"},
    "grammatical_range_accuracy": {"band": 6.5, "justification": "mostly accurate"},
    "all_parts_addressed": True,
    "position_clear": True,
    "off_topic": False,
    "errors": [],
}


def _grade(grader):
    fb = grader.grade(task_type=2, prompt="Discuss public transport.", text=ESSAY, min_words=60)
    assert fb.error is False and fb.band == 6.5
    return fb


@pytest.fixture
def gemini_configs(monkeypatch):
    """Capture the GenerateContentConfig of every Gemini request."""
    configs = []

    class Resp:
        text = json.dumps(EXAMINER)
        candidates = []

    def generate_content(model, contents, config):
        configs.append(config)
        return Resp()

    client = type("C", (), {"models": type("M", (), {"generate_content": staticmethod(generate_content)})()})()
    monkeypatch.setattr(gemini, "_client", lambda: client)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "WRITING_COACH_ENABLED", False)
    return configs


@pytest.fixture
def qwen_bodies(monkeypatch):
    """Capture the JSON body of every Qwen request."""
    bodies = []

    def server(request):
        bodies.append(json.loads(request.content))
        message = {"content": json.dumps(EXAMINER)}
        return httpx.Response(200, json={"choices": [{"message": message, "finish_reason": "stop"}]})

    async def no_sleep(_):
        return None

    monkeypatch.setattr(settings, "QWEN_BASE_URL", "http://qwen.test/v1")
    monkeypatch.setattr(settings, "QWEN_MODEL", "qwen3:14b")
    monkeypatch.setattr(settings, "WRITING_COACH_ENABLED", False)
    monkeypatch.setattr(
        qwen,
        "_client",
        lambda: OpenAICompatClient(
            base_url=settings.QWEN_BASE_URL,
            model=settings.QWEN_MODEL,
            transport=httpx.MockTransport(server),
            sleep=no_sleep,
        ),
    )
    reset_json_schema_cache()
    return bodies


def test_gemini_default_seed_is_unchanged_and_explicit_seed_is_sent(gemini_configs):
    _grade(factory.get_writing_grader("gemini"))
    _grade(gemini.GeminiWritingGrader())
    assert [c.seed for c in gemini_configs] == [GRADING_SEED, GRADING_SEED] and GRADING_SEED == 20261026
    gemini_configs.clear()
    _grade(factory.get_writing_grader("gemini", seed=123))
    assert [c.seed for c in gemini_configs] == [123]
    assert gemini._config("s").seed == GRADING_SEED  # other Gemini callers (speaking, vocabulary) keep the default


def test_qwen_default_seed_is_unchanged_and_explicit_seed_is_sent(qwen_bodies):
    _grade(factory.get_writing_grader("qwen"))
    assert [b["seed"] for b in qwen_bodies] == [GRADING_SEED]
    qwen_bodies.clear()
    _grade(factory.get_writing_grader("qwen", seed=123))
    assert [b["seed"] for b in qwen_bodies] == [123]
    assert qwen.QwenTransport().seed == GRADING_SEED


def test_providers_without_a_seed_refuse_one(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    for provider in ("claude", "mock"):
        with pytest.raises(factory.SeedNotSupported):
            factory.get_writing_grader(provider, seed=1)
        assert factory.get_writing_grader(provider) is not None  # unchanged without a seed
    # The configured provider is checked after fallback: an unconfigured Gemini is the mock.
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    with pytest.raises(factory.SeedNotSupported):
        factory.get_writing_grader(seed=1)
