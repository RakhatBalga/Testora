"""Gemini grading validation suite.

Exercises the failure-handling contract that protects production: a well-formed
response is parsed into a Feedback; every failure mode (malformed JSON, empty
body, exceptions/timeouts, truncation) is surfaced as `error=True` with no
exception escaping — so the router saves the submission as *failed* instead of
persisting a bogus Band-0 grade.
"""
import json

import pytest

from app.services.ai import gemini
from app.services.ai.base import Feedback


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
    "band": 7.0,
    "criteria": {
        "Fluency & Coherence": 7.0,
        "Lexical Resource": 7.0,
        "Grammatical Range & Accuracy": 7.0,
        "Pronunciation": 7.0,
    },
    "summary": "Fluent.",
    "suggestions": [],
}


# ----------------------------- parsing / schema -----------------------------

def test_parse_plain_json():
    assert gemini._parse(json.dumps(_VALID_WRITING))["band"] == 6.5


def test_parse_strips_markdown_code_fence():
    raw = "```json\n" + json.dumps(_VALID_WRITING) + "\n```"
    assert gemini._parse(raw)["criteria"]["Lexical Resource"] == 7.0


def test_to_feedback_maps_all_fields():
    fb = gemini._to_feedback(_VALID_WRITING)
    assert isinstance(fb, Feedback)
    assert fb.band == 6.5
    assert fb.error is False
    assert set(fb.criteria) == set(_VALID_WRITING["criteria"])


def test_to_feedback_derives_band_when_missing():
    data = {**_VALID_WRITING}
    data.pop("band")
    fb = gemini._to_feedback(data)
    assert 6.0 <= fb.band <= 7.0  # mean of the four criteria


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
        {"category": "grammar", "subskill": "articles", "severity": 2,
         "snippet": "in the society", "correction": "in society"},
    ],
}


def test_writing_valid_response(monkeypatch):
    # Examiner-only (disable coach so a single stub response suffices).
    monkeypatch.setattr(gemini.settings, "WRITING_COACH_ENABLED", False)
    monkeypatch.setattr(gemini, "_generate", lambda *a, **k: json.dumps(_EXAMINER_T2))
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text="word " * 300, min_words=250)
    assert fb.error is False
    assert fb.band == 6.5  # mean(6.5,6.5,7.0,6.5)=6.625 -> 6.5
    assert fb.criteria["Task Response"] == 6.5
    assert fb.mistakes and fb.mistakes[0].category == "grammar"  # errors -> mistakes


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
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text="word " * 300, min_words=250)
    assert fb.error is False
    assert fb.band == 6.5
    assert fb.roadmap == []  # no coaching, but grade intact


def test_writing_malformed_json_is_error_not_crash(monkeypatch):
    monkeypatch.setattr(gemini, "_generate", lambda *a, **k: "not json at all {")
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text="essay", min_words=250)
    assert fb.error is True
    assert fb.band == 0.0  # sentinel; router must NOT persist this as a real grade


def test_writing_exception_is_error(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("deadline exceeded")

    monkeypatch.setattr(gemini, "_generate", boom)
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text="essay", min_words=250)
    assert fb.error is True
    assert "deadline exceeded" in fb.summary


def test_writing_truncated_response_is_error(monkeypatch):
    def truncated(*a, **k):
        raise gemini._TruncatedResponse("hit token cap")

    monkeypatch.setattr(gemini, "_generate", truncated)
    fb = gemini.GeminiWritingGrader().grade(task_type=2, prompt="p", text="x", min_words=250)
    assert fb.error is True


# ----------------------------- speaking grader ------------------------------

def test_speaking_valid_response(monkeypatch, tmp_path):
    audio = tmp_path / "a.webm"
    audio.write_bytes(b"fake-audio-bytes")
    # _generate is patched, so no network call; google.genai (a real dependency)
    # provides types.Part for assembling the request.
    monkeypatch.setattr(gemini, "_generate", lambda contents, system: json.dumps(_VALID_SPEAKING))

    fb = gemini.GeminiSpeakingGrader().grade(part=1, questions=["Q"], audio_path=str(audio))
    assert fb.error is False
    assert fb.band == 7.0


def test_speaking_missing_file_is_error(monkeypatch):
    monkeypatch.setattr(gemini, "_generate", lambda contents, system: json.dumps(_VALID_SPEAKING))
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
