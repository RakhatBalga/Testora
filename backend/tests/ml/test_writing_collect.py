
import pytest

from app.infrastructure.ai.base import Feedback
from ml import graders
from ml.collect_writing import collect, load_cache, main
from ml.writing_data import write_essays
from writing_synth import make_essays


class FakeGrader:
    def __init__(self, fail_ids=(), raise_ids=()):
        self.calls = 0
        self.fail_texts = set(fail_ids)
        self.raise_texts = set(raise_ids)

    def grade(self, *, task_type, prompt, text, min_words):
        self.calls += 1
        if text in self.raise_texts:
            raise TimeoutError("provider timed out")
        if text in self.fail_texts:
            return Feedback(band=0, criteria={}, summary="malformed output", error=True)
        fb = Feedback(band=6.5, criteria={"Task Response": 6.0, "Coherence & Cohesion": 7.0,
                                          "Lexical Resource": 6.5, "Grammatical Range & Accuracy": 6.5},
                      summary="ok")
        fb.flags = {"off_topic": False, "position_clear": True}
        return fb


KW = dict(provider="fake", model="m1", prompt_version="pv1")


def test_collect_caches_resumes_and_keys_on_version(tmp_path):
    essays = make_essays(5)
    cache, grader = tmp_path / "c.jsonl", FakeGrader()
    s = collect(essays, grader, cache_path=cache, runs=2, **KW)
    assert (s.requested, s.new_ok, s.failed, grader.calls) == (10, 10, 0, 10)
    rec = next(iter(load_cache(cache).values()))
    assert rec["criteria"] == {"task": 6.0, "coherence": 7.0, "lexical": 6.5, "grammar": 6.5}
    assert rec["flags"]["position_clear"] is True and rec["raw"]["band"] == 6.5
    assert "text" not in rec  # essays are referenced by hash only
    again = collect(essays, grader, cache_path=cache, runs=2, **KW)
    assert again.cached_ok == 10 and grader.calls == 10  # resume: no new calls
    collect(essays, grader, cache_path=cache, runs=1, provider="fake", model="m1", prompt_version="pv2")
    assert grader.calls == 15  # a new prompt version is a new key


def test_failures_are_recorded_counted_and_retried(tmp_path):
    essays = make_essays(4)
    cache = tmp_path / "c.jsonl"
    grader = FakeGrader(fail_ids=[essays[0].text], raise_ids=[essays[1].text])
    s = collect(essays, grader, cache_path=cache, **KW)
    assert s.new_ok == 2 and s.failed == 2 and len(s.failure_reasons) == 2
    records = load_cache(cache)
    assert sum(not r["ok"] for r in records.values()) == 2
    assert all(r["error"] and r["band"] is None for r in records.values() if not r["ok"])
    healed = FakeGrader()
    s2 = collect(essays, healed, cache_path=cache, **KW)
    assert healed.calls == 2 and s2.cached_ok == 2 and s2.new_ok == 2 and s2.failed == 0  # only failures retried
    s3 = collect(essays, FakeGrader(fail_ids=[e.text for e in essays]), cache_path=tmp_path / "d.jsonl",
                 retry_failed=False, abort_after=3, **KW)
    assert s3.aborted and s3.failed == 3


def test_rate_limit_spaces_calls(tmp_path):
    now = [0.0]
    sleeps = []

    def sleep(s):
        sleeps.append(s)
        now[0] += s
    collect(make_essays(4), FakeGrader(), cache_path=tmp_path / "c.jsonl", rps=2.0,
            sleep=sleep, clock=lambda: now[0], **KW)
    assert len(sleeps) == 3 and all(s == pytest.approx(0.5) for s in sleeps)


def test_grade_call_passes_seed_only_when_supported():
    class Seeded:
        def grade(self, *, task_type, prompt, text, min_words, seed=None):
            return seed
    assert graders.grade_call(Seeded(), task_type=2, prompt="p", text="t", min_words=250, seed=9) == 9

    class Plain:
        def grade(self, *, task_type, prompt, text, min_words):
            return "ok"
    assert graders.grade_call(Plain(), task_type=2, prompt="p", text="t", min_words=250, seed=9) == "ok"


def test_adapter_mock_and_unavailable_provider(monkeypatch):
    from app.infrastructure.config import settings
    from app.infrastructure.ai.mock import MockWritingGrader
    before = settings.AI_PROVIDER
    assert isinstance(graders.make_grader("mock"), MockWritingGrader)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    with pytest.raises(graders.ProviderUnavailable):  # must not silently measure the mock
        graders.make_grader("gemini")
    assert settings.AI_PROVIDER == before


def test_cli_mock_run_end_to_end(tmp_path):
    ds, cache = tmp_path / "d.jsonl", tmp_path / "c.jsonl"
    write_essays(ds, make_essays(6, split="test"))
    code = main(["--dataset", str(ds), "--split", "test", "--provider", "mock", "--cache", str(cache), "--runs", "2"])
    assert code == 0
    records = load_cache(cache)
    assert len(records) == 12 and all(r["ok"] for r in records.values())
    assert {r["model"] for r in records.values()} == {"rules-v1"}
