"""The E1 run records what really graded: examiner prompt version, model, seed.

No network: the real factory builds the real Qwen grader, whose HTTP client is
an httpx mock that captures every request. So the prompt selection, the model,
the seed in the request body and the provenance stamping are the production code.
"""

import json

import httpx
import pytest

from app.infrastructure.ai import prompts
from app.infrastructure.ai import qwen as qwen_module
from app.infrastructure.ai.engine import GRADING_SEED
from app.infrastructure.ai.openai_compat import OpenAICompatClient, reset_json_schema_cache
from app.infrastructure.config import settings
from ml import evaluate_writing as ev
from ml import graders
from ml.collect_writing import collect, load_cache, main
from ml.writing_data import Essay, write_essays

EXAMINER_REPLY = {
    "task_response": {"band": 6.5, "justification": "clear position"},
    "coherence_cohesion": {"band": 6.5, "justification": "logical"},
    "lexical_resource": {"band": 7.0, "justification": "good range"},
    "grammatical_range_accuracy": {"band": 6.5, "justification": "mostly accurate"},
    "all_parts_addressed": True,
    "position_clear": True,
    "off_topic": False,
    "errors": [],
}


class Server:
    """Fake OpenAI-compatible server: records each request body, returns one grade."""

    def __init__(self):
        self.bodies: list[dict] = []

    def __call__(self, request):
        self.bodies.append(json.loads(request.content))
        message = {"content": json.dumps(EXAMINER_REPLY)}
        return httpx.Response(200, json={"choices": [{"message": message, "finish_reason": "stop"}]})

    @property
    def systems(self):
        return [b["messages"][0]["content"] for b in self.bodies]

    @property
    def models(self):
        return [b["model"] for b in self.bodies]

    @property
    def seeds(self):
        return [b["seed"] for b in self.bodies]


@pytest.fixture
def qwen(monkeypatch):
    """A configured Qwen provider whose HTTP requests never leave the process."""
    server = Server()

    async def no_sleep(_):
        return None

    def client():
        return OpenAICompatClient(
            base_url=settings.QWEN_BASE_URL,
            model=settings.QWEN_MODEL,
            transport=httpx.MockTransport(server),
            sleep=no_sleep,
        )

    monkeypatch.setattr(settings, "QWEN_BASE_URL", "http://qwen.test/v1")
    monkeypatch.setattr(settings, "QWEN_MODEL", "qwen-default")
    monkeypatch.setattr(settings, "WRITING_COACH_ENABLED", False)
    monkeypatch.setattr(qwen_module, "_client", client)
    reset_json_schema_cache()
    return server


TASK = "Governments should spend money on public transport rather than building new roads. Discuss."
BODY = (
    "Some people believe governments should spend money on public transport rather than "
    "new roads. In my view, buses and trains are the better investment for most cities. "
    "Firstly, public transport moves many people using little space, so traffic falls. "
    "Secondly, it reduces pollution because fewer private cars are used every day. "
    "However, roads are still needed in rural areas where trains do not run. "
    "Overall, public transport should receive most of the money in growing cities. "
)


def essays_long(n=3):
    """Essays that pass the engine's pre-check, so the examiner prompt is really sent."""
    return [
        Essay(
            id=f"e{i}",
            task_type=2,
            prompt=TASK,
            text=BODY * 3 + f"This is the closing remark of candidate number {i}.",
            overall=6.5,
            source="synthetic",
            licence="test",
            split="test",
        )
        for i in range(n)
    ]


def run(cache, essays, examiner, **kw):
    with graders.experiment_run("qwen", examiner=examiner, **kw) as spec:
        return spec, collect(essays, spec.grader, **spec.collect_kwargs(), cache_path=cache)


def test_v1_and_v2_runs_never_share_a_cache_key(tmp_path, qwen, monkeypatch):
    monkeypatch.setattr(settings, "EXAMINER_PROMPT_VERSION", "v2")
    essays, cache = essays_long(), tmp_path / "c.jsonl"
    spec1, s1 = run(cache, essays, "v1")
    assert s1.new_ok == 3 and set(qwen.systems) == {prompts.examiner_system(2, "v1")}
    qwen.bodies.clear()
    spec2, s2 = run(cache, essays, "v2")
    assert (s2.new_ok, s2.cached_ok) == (3, 0)  # v2 is graded, not served from the v1 cache
    assert set(qwen.systems) == {prompts.examiner_system(2, "v2")}
    assert spec1.prompt_version != spec2.prompt_version
    assert (
        prompts.PROMPT_VERSIONS["v1"] in spec1.prompt_version and prompts.PROMPT_VERSIONS["v2"] in spec2.prompt_version
    )
    _, again = run(cache, essays, "v1")
    assert (again.new_ok, again.cached_ok) == (0, 3)  # each version resumes from its own records
    records = list(load_cache(cache).values())
    assert len(records) == 6 and all(r["ok"] for r in records)
    assert {(r["examiner_version"], r["prompt_version"]) for r in records} == {
        ("v1", spec1.prompt_version),
        ("v2", spec2.prompt_version),
    }
    systems = ev.systems_from_cache(load_cache(cache), essays)
    assert sorted(s.detail["examiner_version"] for s in systems) == ["v1", "v2"]
    assert len({s.id for s in systems}) == 2 and len({s.name for s in systems}) == 2
    assert settings.EXAMINER_PROMPT_VERSION == "v2"  # the run restores the app setting


def test_report_states_the_measured_prompt_model_and_seed(tmp_path, qwen):
    essays, cache = essays_long(), tmp_path / "c.jsonl"
    run(cache, essays, "v1")
    systems = ev.systems_from_cache(load_cache(cache), essays)
    report = ev.evaluate(essays, systems, n_boot=0)
    md = ev.render_markdown(report, {"split": "dev", "generated_at": "now", "dataset_sha256": "x"})
    assert "## What was measured" in md
    assert f"| qwen | qwen-default | v1 | `{systems[0].detail['prompt_version']}` | {GRADING_SEED} |" in md
    assert set(qwen.seeds) == {GRADING_SEED}  # the default run sends the production seed


def test_engine_provider_needs_an_explicit_examiner_version(tmp_path, qwen):
    with pytest.raises(graders.RunInputError, match="explicit examiner prompt version"):
        with graders.experiment_run("qwen"):
            pass
    with pytest.raises(graders.RunInputError):
        with graders.experiment_run("qwen", examiner="v9"):
            pass
    ds = tmp_path / "d.jsonl"
    write_essays(ds, essays_long())
    base = ["--dataset", str(ds), "--split", "test", "--provider", "qwen", "--cache", str(tmp_path / "c.jsonl")]
    with pytest.raises(SystemExit, match="examiner prompt version"):
        main(base)
    assert main([*base, "--examiner-version", "v1"]) == 0
    assert {r["examiner_version"] for r in load_cache(tmp_path / "c.jsonl").values()} == {"v1"}


def test_model_is_applied_for_real_or_refused(tmp_path, qwen):
    essays, cache = essays_long(), tmp_path / "c.jsonl"
    spec, _ = run(cache, essays, "v1", model="qwen-other")
    assert spec.model == "qwen-other" and set(qwen.models) == {"qwen-other"}  # reached the transport
    assert {r["model"] for r in load_cache(cache).values()} == {"qwen-other"}
    assert all(r["raw"] is not None and r["ok"] for r in load_cache(cache).values())
    assert settings.QWEN_MODEL == "qwen-default"
    # Providers with a fixed model refuse a label they would not apply.
    with pytest.raises(graders.RunInputError, match="fixed in code"):
        with graders.experiment_run("claude", examiner="v1", model="some-other-model"):
            pass
    with pytest.raises(graders.RunInputError, match="cannot be applied"):
        with graders.experiment_run("mock", model="gemini-2.5-flash"):
            pass


def test_claude_and_mock_models_are_the_real_ones():
    from app.infrastructure.ai import claude, mock

    assert graders.model_name("claude") == claude.MODEL != "unknown"
    assert graders.model_name("mock") == mock.MOCK_MODEL
    assert graders.model_name("claude", claude.ClaudeWritingGrader()) == claude.MODEL


def test_requested_seed_reaches_the_request_and_is_the_one_recorded(tmp_path, qwen):
    essays, cache = essays_long(2), tmp_path / "c.jsonl"
    spec, summary = run(cache, essays, "v1", seed=7)
    assert spec.seed == 7 and summary.new_ok == 2
    assert qwen.seeds == [7, 7]  # in the HTTP body, not only in the label
    assert {(r["seed"], r["base_seed"]) for r in load_cache(cache).values()} == {(7, 7)}
    # Another seed is another key: nothing is served from the seed-7 records.
    qwen.bodies.clear()
    _, other = run(cache, essays, "v1", seed=8)
    assert (other.new_ok, other.cached_ok) == (2, 0) and qwen.seeds == [8, 8]
    # With no --seed the run sends, and records, the production seed.
    qwen.bodies.clear()
    default, _ = run(tmp_path / "d.jsonl", essays, "v1")
    assert default.seed == GRADING_SEED and qwen.seeds == [GRADING_SEED] * 2
    assert {r["seed"] for r in load_cache(tmp_path / "d.jsonl").values()} == {GRADING_SEED}


def test_stability_runs_send_distinct_recorded_seeds(tmp_path, qwen):
    essays, cache = essays_long(2), tmp_path / "c.jsonl"
    with graders.experiment_run("qwen", examiner="v1", seed=100) as spec:
        summary = collect(essays, spec.grader, **spec.collect_kwargs(), cache_path=cache, runs=3)
    assert summary.new_ok == 6
    assert qwen.seeds == [100, 100, 101, 101, 102, 102]  # run-major order, seed = base + run
    records = load_cache(cache).values()
    assert {(r["run"], r["seed"]) for r in records} == {(0, 100), (1, 101), (2, 102)}
    assert {r["base_seed"] for r in records} == {100}
    # The three runs are one system (not three), and the report names the seeds.
    systems = ev.systems_from_cache(load_cache(cache), essays)
    assert len(systems) == 1 and systems[0].detail["run_seeds"] == {"0": 100, "1": 101, "2": 102}
    assert systems[0].id.endswith("|seed100")
    report = ev.evaluate(essays, systems, n_boot=0)
    block = next(b for b in report["systems"] if b["id"] == systems[0].id)
    assert block["stability"]["n_runs"] == 3 and block["stability"]["run_seeds"] == {"0": 100, "1": 101, "2": 102}
    md = ev.render_markdown(report, {"split": "dev", "generated_at": "now", "dataset_sha256": "x"})
    assert "| 3 | 100, 101, 102 |" in md and "| 100, 101, 102 |" in md.split("## What was measured")[1]
    # Resume: every run finds its own seed's records.
    qwen.bodies.clear()
    with graders.experiment_run("qwen", examiner="v1", seed=100) as spec:
        again = collect(essays, spec.grader, **spec.collect_kwargs(), cache_path=cache, runs=3)
    assert again.cached_ok == 6 and qwen.bodies == []


def test_cli_seed_is_real_for_qwen_and_refused_where_no_seed_exists(tmp_path, qwen, monkeypatch):
    ds = tmp_path / "d.jsonl"
    write_essays(ds, essays_long(1))
    base = ["--dataset", str(ds), "--split", "test", "--cache", str(tmp_path / "c.jsonl")]
    assert main([*base, "--provider", "qwen", "--examiner-version", "v1", "--seed", "41", "--runs", "2"]) == 0
    assert qwen.seeds == [41, 42]
    assert sorted(r["seed"] for r in load_cache(tmp_path / "c.jsonl").values()) == [41, 42]
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(SystemExit, match="does not take a sampling seed"):
        main([*base, "--provider", "claude", "--examiner-version", "v1", "--seed", "41"])
    with pytest.raises(SystemExit, match="takes no seed"):
        main([*base, "--provider", "mock", "--seed", "41"])
    with graders.experiment_run("claude", examiner="v1") as spec:
        assert spec.seed is None  # the Messages API has no seed: nothing is recorded as sent
    with graders.experiment_run("mock") as spec:
        assert spec.seed is None and spec.examiner_version is None
    with pytest.raises(graders.RunInputError, match="does not use the examiner prompt"):
        with graders.experiment_run("mock", examiner="v1"):
            pass


def test_registered_grader_gets_the_seed_or_the_call_is_refused(tmp_path):
    from app.infrastructure.ai.base import Feedback

    class Seeded:
        def __init__(self):
            self.seeds = []

        def grade(self, *, task_type, prompt, text, min_words, seed=None):
            self.seeds.append(seed)
            return Feedback(band=6.0, criteria={}, summary="s")

    seeded = Seeded()
    graders.register_grader("seeded", lambda: seeded)
    try:
        with graders.experiment_run("seeded", seed=7) as spec:
            collect(essays_long(2), spec.grader, **spec.collect_kwargs(), cache_path=tmp_path / "s.jsonl", runs=2)
    finally:
        graders.unregister_grader("seeded")
    assert spec.seed == 7 and seeded.seeds == [7, 7, 8, 8]

    class Plain:
        def grade(self, *, task_type, prompt, text, min_words):
            return Feedback(band=6.0, criteria={}, summary="s")

    with pytest.raises(graders.RunInputError, match="takes no seed"):  # never recorded as if applied
        collect(essays_long(1), Plain(), provider="p", model="m", prompt_version="v", seed=3, cache_path=tmp_path / "p")


def test_result_with_other_provenance_is_stored_as_a_failure(tmp_path, qwen):
    essays, cache = essays_long(), tmp_path / "c.jsonl"
    with graders.experiment_run("qwen", examiner="v1") as spec:
        kwargs = spec.collect_kwargs()
        wrong_model = collect(essays, spec.grader, **{**kwargs, "model": "label-only"}, cache_path=cache)
    assert wrong_model.failed == 3 and wrong_model.new_ok == 0
    assert all("provenance mismatch" in r["error"] for r in load_cache(cache).values())
    # Grading under v2 while the run records the v1 key is caught the same way.
    with graders.experiment_run("qwen", examiner="v2") as spec:
        wrong_prompt = collect(essays, spec.grader, **kwargs, cache_path=tmp_path / "d.jsonl")
    assert wrong_prompt.failed == 3
