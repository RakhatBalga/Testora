import json

import pytest

from app.infrastructure.ai.base import Feedback
from ml import evaluate_writing as ev
from ml import graders
from ml.collect_writing import collect, load_cache
from ml.writing_data import Essay, RaterScore, build_manifest, write_essays
from writing_synth import make_essays


def provider(labels, fn, cap_flags=None):
    class G:
        def grade(self, *, task_type, prompt, text, min_words):
            band = fn(labels[text])
            if band is None:
                raise RuntimeError("quota exceeded")
            fb = Feedback(band=band, criteria={"Task Response": band, "Lexical Resource": band}, summary="s")
            if cap_flags is not None:
                fb.flags = cap_flags
            return fb
    return G()


@pytest.fixture
def setup(tmp_path):
    test = make_essays(40, n_prompts=8, seed=11, split="test", prefix="t", with_criteria=True)
    train = make_essays(40, n_prompts=8, seed=12, split="train", prefix="r")
    labels = {e.text: e.overall for e in test}
    cache = tmp_path / "cache.jsonl"
    kw = dict(cache_path=cache, runs=3)
    # flat 7.0 grader (the compression problem), accurate grader, flaky grader.
    collect(test, provider(labels, lambda y: 7.0), provider="flat", model="m", prompt_version="v1", **kw)
    noise = iter(range(10 ** 6))
    collect(test, provider(labels, lambda y: min(9, max(0, y + [0, 0.5, -0.5, 0, 0][next(noise) % 5]))),
            provider="good", model="m", prompt_version="v1", **kw)
    flaky_calls = iter(range(10 ** 6))
    collect(test, provider(labels, lambda y: None if next(flaky_calls) % 4 == 0 else y),
            provider="flaky", model="m", prompt_version="v1", cache_path=cache, runs=1)
    return test, train, load_cache(cache), cache


def run(setup, **kw):
    test, train, records, _ = setup
    systems = ev.systems_from_cache(records, test)
    return ev.evaluate(test, systems, train_essays=train, n_boot=200, **kw), systems


def block(report, name):
    return next(b for b in report["systems"] if b["name"] == name)


def test_results_table_separates_flat_constant_and_good(setup):
    report, _ = run(setup)
    flat, good = block(report, "flat:m")["targets"]["overall"], block(report, "good:m")["targets"]["overall"]
    assert flat["qwk"] == pytest.approx(0, abs=1e-9) and flat["mode_share"] == 1.0 and flat["sd_ratio"] == 0
    assert good["qwk"] > 0.85 and good["qwk"] > flat["qwk"]
    for name in ("constant mean", "constant mode"):
        c = block(report, name)["targets"]["overall"]
        assert c["qwk"] is not None and abs(c["qwk"]) < 0.2
        assert c["mae"] < 1.5
    assert block(report, "constant mode")["detail"]["fit_on"] == "train split"
    assert "ci95" in good and good["ci95"]["qwk"]["lo"] < good["qwk"] < good["ci95"]["qwk"]["hi"] + 1e-9


def test_failures_reduce_coverage_and_common_set_not_silently_dropped(setup):
    report, _ = run(setup)
    flaky = block(report, "flaky:m")
    assert flaky["coverage"]["failed"] == 10 and flaky["coverage"]["covered"] == 30
    assert flaky["coverage"]["failure_reasons"]
    assert report["n_common"] == 30
    assert any("covered by every system" in w for w in report["warnings"])
    assert block(report, "good:m")["targets"]["overall"]["n"] == 30


def test_stability_and_paired_comparison(setup):
    report, _ = run(setup, reference="good:m")
    st = block(report, "good:m")["stability"]
    assert st["n_runs"] == 3 and st["icc_2_1"] is not None
    assert block(report, "flat:m")["stability"]["mean_within_essay_sd"] == 0
    vs_flat = next(p for p in report["paired_vs_reference"] if p["b"] == "flat:m")
    assert vs_flat["metrics"]["qwk"]["diff"] > 0.5 and vs_flat["metrics"]["qwk"]["lo"] > 0


def test_per_criterion_metrics_and_markdown(setup):
    report, _ = run(setup, ci_criteria=True)
    good = block(report, "good:m")["targets"]
    assert "task" in good and "lexical" in good and good["task"]["n"] == 30
    md = ev.render_markdown({**report, "meta": {}}, {"split": "test", "generated_at": "now", "dataset_sha256": "x",
                                                      "protocol_deviations": ["demo deviation"]})
    assert "| good:m |" in md and "constant mean" in md and "WARNING: demo deviation" in md
    assert "Paired bootstrap" in md and "Run-to-run stability" in md


def test_human_human_ceiling_row():
    gold = []
    for i, (a, b) in enumerate([(6.0, 6.0), (6.5, 6.0), (7.0, 7.5), (5.5, 5.5), (6.0, 6.5), (7.0, 7.0)]):
        gold.append(Essay(id=f"g{i}", task_type=2, prompt="p", text=f"gold {i}", overall=a, source="x", split="gold",
                          rater_scores=[RaterScore(rater_id="T1", overall=a), RaterScore(rater_id="T2", overall=b)]))
    report = ev.evaluate(gold, [], n_boot=50)
    ceiling = block(report, "human vs human (ceiling)")
    assert ceiling["kind"] == "human" and ceiling["targets"]["overall"]["n"] == 6
    assert ceiling["targets"]["overall"]["qwk"] > 0.7


def test_cap_hit_rate_uses_flags_when_present(tmp_path):
    test = make_essays(10, split="test")
    labels = {e.text: e.overall for e in test}
    cache = tmp_path / "c.jsonl"
    collect(test, provider(labels, lambda y: 6.0, cap_flags={"off_topic": True}), cache_path=cache,
            provider="capped", model="m", prompt_version="v")
    report = ev.evaluate(test, ev.systems_from_cache(load_cache(cache), test), n_boot=0)
    assert block(report, "capped:m")["cap_hit_rate"] == 1.0


def test_cli_protects_test_split_and_checks_prereg(tmp_path, setup):
    test, train, _, cache = setup
    ds, manifest = tmp_path / "d.jsonl", tmp_path / "m.json"
    essays = test + train
    write_essays(ds, essays)
    manifest.write_text(json.dumps(build_manifest(essays, [], seed=1, test_fraction=0.3)))
    base = ["--dataset", str(ds), "--manifest", str(manifest), "--split", "test", "--cache", str(cache),
            "--n-boot", "50", "--only", "good", "flat"]
    with pytest.raises(SystemExit, match="protected"):
        ev.main(base)
    prereg = tmp_path / "prereg.md"
    assert ev.main([*base, "--write-prereg", str(prereg), "--primary", "good:m"]) == 0
    with pytest.raises(FileExistsError):
        ev.main([*base, "--write-prereg", str(prereg)])
    out = tmp_path / "rep"
    assert ev.main([*base, "--prereg", str(prereg), "--out", str(out)]) == 0
    report = json.loads((tmp_path / "rep.json").read_text())
    assert report["meta"]["prereg_sha256"] and report["meta"]["protocol_deviations"] == []
    assert report["meta"]["verdict"]["qwk_point_ok"] is True
    assert (tmp_path / "rep.md").read_text().startswith("# E1")
    # A system outside the frozen protocol is reported as a deviation.
    ev.main([*base[:-3], "--only", "good", "flat", "flaky", "--prereg", str(prereg), "--out", str(tmp_path / "rep2")])
    dev = json.loads((tmp_path / "rep2.json").read_text())["meta"]["protocol_deviations"]
    assert any("flaky" in d for d in dev)
    # dev split is flagged as non-reportable; unregistered test is recorded when allowed.
    ev.main([*base, "--allow-unregistered", "--out", str(tmp_path / "rep3")])
    assert "WITHOUT a pre-registered protocol" in (tmp_path / "rep3.md").read_text()


def test_cli_run_mock_and_trained_bundle_leak_guard(tmp_path):
    pytest.importorskip("sklearn")
    pytest.importorskip("joblib")
    from ml.train_writing import train
    train_set = make_essays(50, n_prompts=6, seed=1)
    test = make_essays(20, n_prompts=4, seed=2, split="test", prefix="t")
    ds = tmp_path / "d.jsonl"
    write_essays(ds, train_set + test)
    train(train_set, folds=3, out_dir=tmp_path / "model")
    bundle = tmp_path / "model" / "writing_models.joblib"
    out = tmp_path / "rep"
    assert ev.main(["--dataset", str(ds), "--split", "test", "--allow-unregistered", "--run-mock",
                    "--mock-cache", str(tmp_path / "mock.jsonl"), "--model-bundle", str(bundle),
                    "--n-boot", "50", "--out", str(out)]) == 0
    names = [b["name"] for b in json.loads((tmp_path / "rep.json").read_text())["systems"]]
    assert {"constant mean", "constant mode", "ridge", "gbm", "mock:rules-v1"} <= set(names)
    with pytest.raises(ValueError, match="trained on"):
        ev.main(["--dataset", str(ds), "--split", "train", "--model-bundle", str(bundle), "--n-boot", "10"])
