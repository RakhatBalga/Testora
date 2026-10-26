"""Gemini grading validation suite.

Exercises the failure-handling contract that protects production: a well-formed
response is parsed into a Feedback; every failure mode (malformed JSON, empty
body, exceptions/timeouts, truncation) is surfaced as `error=True` with no
exception escaping — so the router saves the submission as *failed* instead of
persisting a bogus Band-0 grade.
"""

import json

import pytest

from app.infrastructure.ai import gemini
from google.genai import errors as genai_errors


_VALID_WRITING = {
    "band": 6.5,
    "criteria": {
        "Task Achievement": 6.0,
        "Coherence & Cohesion": 6.5,
        "Lexical Resource": 7.0,
        "Grammatical Range & Accuracy": 6.5,
    },
    "summary": "Solid response.",
    "suggestions": ["Use more cohesive devices."],
}

_VALID_SPEAKING = {
    "fluency_coherence": {"band": 7.0, "justification": "fluent"},
    "lexical_resource": {"band": 7.0, "justification": "varied"},
    "grammatical_range_accuracy": {"band": 7.0, "justification": "accurate"},
    "pronunciation": {"band": 7.0, "justification": "clear"},
    "summary": "Fluent.",
    "suggestions": [],
}

_VALID_ESSAY = (
    "Some people believe that schools should teach children how to contribute to society. "
    "However, parents also shape behaviour because children copy what they see at home. "
    "In my view, both sides matter, but family influence is usually stronger in the early years. "
    "Schools can provide rules, teamwork, and civic knowledge, while parents can model kindness, "
    "responsibility, and honesty every day. This combination gives children practical guidance "
    "and a stable set of values."
)


# ----------------------------- parsing / schema -----------------------------


def test_parse_plain_json():
    assert gemini._parse(json.dumps(_VALID_WRITING))["band"] == 6.5


def test_parse_strips_markdown_code_fence():
    raw = "```json\n" + json.dumps(_VALID_WRITING) + "\n```"
    assert gemini._parse(raw)["criteria"]["Lexical Resource"] == 7.0


def test_parse_strips_think_block_and_prose():
    raw = "<think>reasoning</think>Here you go: " + json.dumps(_VALID_WRITING) + " thanks"
    assert gemini._parse(raw)["band"] == 6.5


# ----------------------------- writing grader (two-stage) -------------------
# The redesigned grader runs an Examiner call (constrained JSON schema) and an
# optional Coach call. Stubs accept **kwargs since grade() passes schema/temp.

_EXAMINER_T2 = {
    "task_response": {"band": 6.5, "justification": "clear position"},
    "coherence_cohesion": {"band": 6.5, "justification": "logical"},
    "lexical_resource": {"band": 7.0, "justification": "good range"},
    "grammatical_range_accuracy": {"band": 6.5, "justification": "mostly accurate"},
    "all_parts_addressed": True,
    "position_clear": True,
    "off_topic": False,
    "errors": [
        {
            "category": "grammar",
            "subskill": "articles",
            "severity": 2,
            "snippet": "in the society",
            "correction": "in society",
        },
    ],
}


def test_writing_valid_response(monkeypatch):
    # Examiner-only (disable coach so a single stub response suffices).
    monkeypatch.setattr(gemini.settings, "WRITING_COACH_ENABLED", False)
    monkeypatch.setattr(gemini, "_generate", lambda *a, **k: json.dumps(_EXAMINER_T2))
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert fb.error is False
    assert fb.band == 6.5  # mean(6.5,6.5,7.0,6.5)=6.625 -> 6.5
    assert fb.criteria["Task Response"] == 6.5
    # "in the society" is not in the essay, so the hallucinated mistake is dropped.
    assert fb.mistakes == [] and fb.unverified_snippets == 1
    assert fb.provider == "gemini" and fb.prompt_version and fb.model


def test_writing_verbatim_error_becomes_mistake(monkeypatch):
    examiner = {
        **_EXAMINER_T2,
        "errors": [
            {
                "category": "grammar",
                "subskill": "articles",
                "severity": 2,
                "snippet": "Schools can provide rules",
                "correction": "Schools can set rules",
            },
        ],
    }
    monkeypatch.setattr(gemini.settings, "WRITING_COACH_ENABLED", False)
    monkeypatch.setattr(gemini, "_generate", lambda *a, **k: json.dumps(examiner))
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert fb.mistakes and fb.mistakes[0].category == "grammar"


def test_writing_schema_failure_is_reasked_once(monkeypatch):
    replies = iter(["not json", json.dumps(_EXAMINER_T2)])
    monkeypatch.setattr(gemini.settings, "WRITING_COACH_ENABLED", False)
    monkeypatch.setattr(gemini, "_generate", lambda *a, **k: next(replies))
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert fb.error is False and fb.band == 6.5


def test_writing_passes_identical_cold_temperature(monkeypatch):
    seen = {}

    def gen(contents, system, **k):
        seen.update(k)
        return json.dumps(_EXAMINER_T2)

    monkeypatch.setattr(gemini.settings, "WRITING_COACH_ENABLED", False)
    monkeypatch.setattr(gemini, "_generate", gen)
    gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert seen["temperature"] == 0.1


def test_writing_coach_failure_still_returns_examiner_grade(monkeypatch):
    # Examiner succeeds, Coach raises -> grade still returned (coaching is enrichment).
    calls = {"n": 0}

    def gen(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps(_EXAMINER_T2)
        raise TimeoutError("coach down")

    monkeypatch.setattr(gemini.settings, "WRITING_COACH_ENABLED", True)
    monkeypatch.setattr(gemini, "_generate", gen)
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert fb.error is False
    assert fb.band == 6.5
    assert fb.roadmap == []  # no coaching, but grade intact


def test_writing_coach_unsupported_quotes_are_not_persisted(monkeypatch):
    coach = {
        "strengths": [
            'Develops the idea of "family influence".',
            'Mentions the invented phrase "community dashboard".',
        ],
        "weaknesses": ['The examiner error "in the society" needs attention.'],
        "priorities": [
            'Replace "in the society" with a cleaner general noun phrase.',
            'Fix the invented phrase "community dashboard".',
        ],
        "roadmap": [
            {
                "target_band": 7.0,
                "actions": [
                    'Make "family influence" more specific.',
                    'Remove "community dashboard".',
                ],
            }
        ],
        "why_not_higher_band": 'To reach 7.0, make "family influence" more specific.',
        "summary": 'Do not invent "community dashboard".',
    }
    calls = {"n": 0}

    def gen(*a, **k):
        calls["n"] += 1
        return json.dumps(_EXAMINER_T2 if calls["n"] == 1 else coach)

    monkeypatch.setattr(gemini.settings, "WRITING_COACH_ENABLED", True)
    monkeypatch.setattr(gemini, "_generate", gen)

    fb = gemini.GeminiWritingGrader().grade(
        task_type=2,
        prompt="p",
        text=_VALID_ESSAY + " Such values matter in the society.",
        min_words=60,
    )

    assert fb.error is False
    assert fb.strengths == ['Develops the idea of "family influence".']
    assert fb.weaknesses == ['The examiner error "in the society" needs attention.']
    assert fb.suggestions == ['Replace "in the society" with a cleaner general noun phrase.']
    assert fb.roadmap == [{"target_band": 7.0, "actions": ['Make "family influence" more specific.']}]
    assert fb.summary.startswith("Estimated Band 6.5.")
    assert fb.why_not_higher_band == 'To reach 7.0, make "family influence" more specific.'


def test_writing_malformed_json_is_error_not_crash(monkeypatch):
    calls = {"n": 0}

    def gen(*a, **k):
        calls["n"] += 1
        return "not json at all {"

    monkeypatch.setattr(gemini, "_generate", gen)
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert fb.error is True
    assert fb.band == 0.0  # sentinel; router must NOT persist this as a real grade
    assert calls["n"] == 2  # one re-ask on a schema failure, then give up


def test_writing_exception_is_error_with_sanitized_message(monkeypatch):
    def boom(*a, **k):
        raise PermissionError("403 PERMISSION_DENIED API key project-123")

    monkeypatch.setattr(gemini, "_generate", boom)
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert fb.error is True
    assert "403" not in fb.summary and "project-123" not in fb.summary
    assert fb.summary.startswith("Automatic grading could not be completed")


def test_writing_truncated_response_is_error(monkeypatch):
    def truncated(*a, **k):
        raise gemini._TruncatedResponse("hit token cap")

    monkeypatch.setattr(gemini, "_generate", truncated)
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text=_VALID_ESSAY, min_words=60)
    assert fb.error is True


# ----------------------------- speaking grader ------------------------------


def test_speaking_valid_response(monkeypatch, tmp_path):
    audio = tmp_path / "a.webm"
    audio.write_bytes(b"fake-audio-bytes")
    # _generate is patched, so no network call; google.genai (a real dependency)
    # provides types.Part for assembling the request.
    monkeypatch.setattr(gemini, "_generate", lambda contents, system, **k: json.dumps(_VALID_SPEAKING))

    fb = gemini.GeminiSpeakingGrader().grade(part=1, questions=["Q"], audio_path=str(audio))
    assert fb.error is False
    assert fb.band == 7.0
    assert fb.provider == "gemini" and fb.prompt_version


def test_speaking_overall_never_taken_from_model_and_bands_clamped(monkeypatch, tmp_path):
    audio = tmp_path / "a.webm"
    audio.write_bytes(b"x")
    reply = {
        **_VALID_SPEAKING,
        "band": 9.0,
        "pronunciation": {"band": 12, "justification": ""},
        "fluency_coherence": {"band": 6.3, "justification": ""},
    }
    monkeypatch.setattr(gemini, "_generate", lambda contents, system, **k: json.dumps(reply))
    fb = gemini.GeminiSpeakingGrader().grade(part=1, questions=["Q"], audio_path=str(audio))
    assert fb.criteria["Pronunciation"] == 9.0
    assert fb.criteria["Fluency & Coherence"] == 6.5
    assert fb.band == 7.5  # mean(6.5, 7, 7, 9) = 7.375 -> 7.5


def test_speaking_nan_or_missing_band_is_error(monkeypatch, tmp_path):
    audio = tmp_path / "a.webm"
    audio.write_bytes(b"x")
    bad = json.dumps(_VALID_SPEAKING).replace('"band": 7.0', '"band": NaN', 1)
    monkeypatch.setattr(gemini, "_generate", lambda contents, system, **k: bad)
    fb = gemini.GeminiSpeakingGrader().grade(part=1, questions=["Q"], audio_path=str(audio))
    assert fb.error is True


def test_speaking_missing_file_is_error(monkeypatch):
    monkeypatch.setattr(gemini, "_generate", lambda contents, system, **k: json.dumps(_VALID_SPEAKING))
    fb = gemini.GeminiSpeakingGrader().grade(part=1, questions=["Q"], audio_path="/no/such/file.webm")
    assert fb.error is True


# ----------------------------- retry / backoff ------------------------------


def test_generate_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    class _Resp:
        text = json.dumps(_VALID_WRITING)
        candidates = []

    def flaky(model, contents, config):
        calls["n"] += 1
        if calls["n"] < 2:
            raise ConnectionError("transient")
        return _Resp()

    fake_client = type("C", (), {"models": type("M", (), {"generate_content": staticmethod(flaky)})()})()
    monkeypatch.setattr(gemini, "_client", lambda: fake_client)
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)  # no real backoff wait

    out = gemini._generate(["x"], "system")
    assert json.loads(out)["band"] == 6.5
    assert calls["n"] == 2  # retried once


def test_generate_gives_up_after_max_attempts(monkeypatch):
    def always_fail(model, contents, config):
        raise ConnectionError("down")

    fake_client = type("C", (), {"models": type("M", (), {"generate_content": staticmethod(always_fail)})()})()
    monkeypatch.setattr(gemini, "_client", lambda: fake_client)
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)

    with pytest.raises(ConnectionError):
        gemini._generate(["x"], "system")


def _fake_client(fn):
    return type("C", (), {"models": type("M", (), {"generate_content": staticmethod(fn)})()})()


def test_generate_does_not_retry_permanent_4xx(monkeypatch):
    calls = {"n": 0}

    def bad_key(model, contents, config):
        calls["n"] += 1
        raise genai_errors.ClientError(403, {"error": {"message": "API key invalid", "status": "PERMISSION_DENIED"}})

    monkeypatch.setattr(gemini, "_client", lambda: _fake_client(bad_key))
    monkeypatch.setattr(gemini.time, "sleep", lambda s: pytest.fail("must not back off on 403"))
    with pytest.raises(genai_errors.ClientError):
        gemini._generate(["x"], "system")
    assert calls["n"] == 1


def test_generate_retries_429_and_5xx(monkeypatch):
    calls = {"n": 0}
    sleeps = []

    class _Resp:
        text = "{}"
        candidates = []

    def flaky(model, contents, config):
        calls["n"] += 1
        if calls["n"] == 1:
            raise genai_errors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})
        if calls["n"] == 2:
            raise genai_errors.ServerError(503, {"error": {"message": "busy", "status": "UNAVAILABLE"}})
        return _Resp()

    monkeypatch.setattr(gemini, "_client", lambda: _fake_client(flaky))
    monkeypatch.setattr(gemini.time, "sleep", sleeps.append)
    assert gemini._generate(["x"], "system") == "{}"
    assert calls["n"] == 3 and sleeps == [1.0, 2.0]


def test_config_passes_seed_and_low_temperature():
    cfg = gemini._config("s", temperature=0.1, model="gemini-2.5-flash")
    assert cfg.seed is not None and cfg.temperature == 0.1
