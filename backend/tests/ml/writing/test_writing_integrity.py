"""Regression tests for E1 integrity gaps found in review (leakage, protocol, ids, coverage, stability)."""

import json
import random

import pytest

from app.infrastructure.ai.base import Feedback
from ml import evaluate_writing as ev
from ml import writing_stats as ws
from ml.collect_writing import collect, load_cache
from ml.writing_data import (
    Essay,
    assign_public_splits,
    assign_public_splits_report,
    build_manifest,
    read_essays,
    verify_manifest,
    write_essays,
)
from writing_synth import make_essays


class Grader:
    def __init__(self, labels, fn):
        self.labels, self.fn = labels, fn

    def grade(self, *, task_type, prompt, text, min_words, seed=0):
        band = self.fn(self.labels[text], seed)
        if band is None:
            raise RuntimeError("fail")
        return Feedback(band=band, criteria={}, summary="s")


@pytest.fixture
def test_set():
    essays = make_essays(30, n_prompts=6, seed=11, split="test", prefix="t")
    return essays, {e.text: e.overall for e in essays}


def systems_of(cache, essays):
    return ev.systems_from_cache(load_cache(cache), essays)


# --- 1. prompt leakage -------------------------------------------------------------------------------


def test_prompts_shared_with_gold_or_dev_never_land_in_train():
    pub = make_essays(40, n_prompts=8, seed=1, split="train", prefix="p")
    gold = [
        e.model_copy(update={"id": f"g{i}", "split": "gold"})
        for i, e in enumerate(make_essays(10, n_prompts=8, seed=2))
    ]
    out = assign_public_splits(gold + pub, test_fraction=0.3, seed=42)
    train_prompts = {e.prompt_id for e in out if e.split == "train"}
    assert not {e.prompt_id for e in out if e.split == "gold"} & train_prompts
    assert all(e.split == "test" for e in out if e.id.startswith("p"))  # every public prompt is a gold prompt


def test_verify_manifest_reports_train_test_gold_prompt_overlap():
    train = make_essays(10, n_prompts=2, prefix="a")
    leaked = [
        e.model_copy(update={"id": f"x{i}", "split": "gold", "text": e.text + " other", "text_hash": ""})
        for i, e in enumerate(make_essays(4, n_prompts=2, prefix="b"))
    ]
    leaked = [Essay.model_validate({**e.model_dump(), "text_hash": ""}) for e in leaked]
    essays = train + leaked
    problems = verify_manifest(essays, build_manifest(essays, [], seed=1, test_fraction=0.3))
    assert any("prompt groups appear in both train and gold" in p for p in problems)


# --- 6. balanced assignment --------------------------------------------------------------------------


def test_dominant_prompt_does_not_overshoot_the_test_share():
    big = [
        Essay(
            id=f"b{i}",
            task_type=2,
            prompt="Same big prompt" if i < 70 else f"P{i}",
            text=f"essay {i} " * 30,
            overall=6.0,
            source="s",
        )
        for i in range(100)
    ]
    for seed in range(5):
        out, info = assign_public_splits_report(big, test_fraction=0.3, seed=seed)
        share = sum(e.split == "test" for e in out) / 100
        assert abs(share - 0.3) <= 0.05 and info["warning"] is None


def test_unreachable_share_warns():
    pool = [
        Essay(id=f"b{i}", task_type=2, prompt="One prompt", text=f"essay {i}", overall=6.0, source="s")
        for i in range(20)
    ]
    _, info = assign_public_splits_report(pool, test_fraction=0.3)
    assert info["warning"] and info["achieved_test_share"] in (0.0, 1.0)


# --- 5. stale hashes ---------------------------------------------------------------------------------


def test_edited_essay_with_stale_hash_is_rejected(tmp_path, test_set):
    essays, _ = test_set
    path = tmp_path / "ds.jsonl"
    write_essays(path, essays)
    rows = path.read_text().splitlines()
    row = json.loads(rows[0])
    row["text"] = "Totally different essay text now. " * 40
    rows[0] = json.dumps(row)
    path.write_text("\n".join(rows) + "\n")
    with pytest.raises(ValueError, match="not a valid"):
        read_essays(path)
    with pytest.raises(ValueError, match="text_hash"):
        Essay.model_validate({**essays[0].model_dump(), "prompt": essays[0].prompt, "text_hash": "0" * 64})


# --- 3. unique system ids ----------------------------------------------------------------------------


def test_different_seeds_get_unique_names_and_stable_ids(tmp_path, test_set):
    essays, labels = test_set
    cache = tmp_path / "c.jsonl"
    kw = dict(provider="gem", model="m", prompt_version="v1", cache_path=cache)
    collect(essays, Grader(labels, lambda y, s: y), seed=0, **kw)
    collect(essays, Grader(labels, lambda y, s: 7.0), seed=1, **kw)
    systems = systems_of(cache, essays)
    assert len({s.name for s in systems}) == 2 and len({s.id for s in systems}) == 2
    report = ev.evaluate(essays, systems, n_boot=30, reference=systems[0].id)
    assert report["reference"] == systems[0].name
    assert len({p["b"] for p in report["paired_vs_reference"]}) == len(report["paired_vs_reference"])


# --- 2. protocol -------------------------------------------------------------------------------------


def _prereg(system, **extra):
    return {
        "systems": [{"provider": "gem", "model": "m", "prompt_version": "v1", "seed": 0, "id": system.id}],
        "primary_id": system.id,
        **extra,
    }


def test_primary_is_matched_by_stable_id_when_display_name_gains_a_suffix(tmp_path, test_set):
    essays, labels = test_set
    cache = tmp_path / "c.jsonl"
    collect(essays, Grader(labels, lambda y, s: y), provider="gem", model="m", prompt_version="v1", cache_path=cache)
    first = systems_of(cache, essays)[0]
    prereg = _prereg(first)
    collect(essays, Grader(labels, lambda y, s: y), provider="gem", model="m", prompt_version="v2", cache_path=cache)
    systems = systems_of(cache, essays)
    assert first.name not in {s.name for s in systems}  # name became gem:m@v1
    report = ev.evaluate(essays, systems, n_boot=30)
    verdict = ev.threshold_verdict(prereg, report)
    assert verdict["primary_id"] == first.id and verdict["qwk_point_ok"] and verdict["all_ok"]
    deviations = ev.check_protocol(prereg, report, "test")
    assert any("gem:m@v2" in d and "not pre-registered" in d for d in deviations)


def test_missing_primary_fails_loudly(tmp_path, test_set):
    essays, labels = test_set
    cache = tmp_path / "c.jsonl"
    collect(essays, Grader(labels, lambda y, s: y), provider="gem", model="m", prompt_version="v1", cache_path=cache)
    report = ev.evaluate(essays, systems_of(cache, essays), n_boot=30)
    with pytest.raises(ValueError, match="not in the evaluated systems"):
        ev.threshold_verdict({"primary_id": "gem|m|v9|seed0"}, report)
    with pytest.raises(ValueError, match="no primary"):
        ev.threshold_verdict({}, report)


def test_dataset_hash_and_fingerprints_checked_without_a_manifest(tmp_path, test_set):
    essays, labels = test_set
    cache = tmp_path / "c.jsonl"
    collect(essays, Grader(labels, lambda y, s: y), provider="gem", model="m", prompt_version="v1", cache_path=cache)
    system = systems_of(cache, essays)[0]
    report = ev.evaluate(essays, [system], n_boot=30)
    prereg = _prereg(system, dataset_sha256="deadbeef", split_fingerprints={"test": "x"})
    deviations = ev.check_protocol(prereg, report, "test", dataset_sha256="cafe", fingerprints={"test": "y"})
    assert any("dataset file hash" in d for d in deviations) and any("fingerprint differs" in d for d in deviations)
    ok = _prereg(system, dataset_sha256="cafe", split_fingerprints={"test": "y"})
    assert ev.check_protocol(ok, report, "test", dataset_sha256="cafe", fingerprints={"test": "y"}) == []
    assert any("no pre-registered fingerprint" in d for d in ev.check_protocol(_prereg(system), report, "test"))


# --- 4. coverage -------------------------------------------------------------------------------------


def test_selective_failures_fail_the_coverage_threshold(tmp_path, test_set):
    essays, labels = test_set
    cache = tmp_path / "c.jsonl"
    # The model "fails" on every hard essay, so it looks perfect on the easy ones.
    collect(
        essays,
        Grader(labels, lambda y, s: y if y >= 6 else None),
        provider="gem",
        model="m",
        prompt_version="v1",
        cache_path=cache,
        retry_failed=False,
    )
    system = systems_of(cache, essays)[0]
    report = ev.evaluate(essays, [system], n_boot=100)
    block = next(b for b in report["systems"] if b["id"] == system.id)
    assert block["coverage"]["rate"] < 0.95 and block["own_overall"]["n"] == block["coverage"]["covered"]
    verdict = ev.threshold_verdict(_prereg(system), report)
    assert verdict["coverage_ok"] is False and verdict["all_ok"] is False
    assert verdict["coverage"]["expected"] == 30


# --- 7. cluster bootstrap default ---------------------------------------------------------------------


def test_cluster_bootstrap_is_default_when_prompts_repeat_and_widens_the_ci():
    rng = random.Random(0)
    y, p, clusters = [], [], []
    for g in range(10):
        offset = rng.choice([-1, -0.5, 0, 0.5, 1])
        for _ in range(20):
            t = rng.choice([5.0, 5.5, 6, 6.5, 7, 7.5])
            y.append(t)
            p.append(min(9, max(0, t + offset + rng.choice([-0.5, 0, 0.5]))))
            clusters.append(g)
    iid = ws.bootstrap_ci(y, p, names=("mae",), n_boot=600)["mae"]
    clu = ws.bootstrap_ci(y, p, names=("mae",), n_boot=600, clusters=clusters)["mae"]
    assert clu["hi"] - clu["lo"] > iid["hi"] - iid["lo"]


def test_evaluate_resolves_cluster_default(tmp_path, test_set):
    essays, labels = test_set
    cache = tmp_path / "c.jsonl"
    collect(essays, Grader(labels, lambda y, s: y), provider="gem", model="m", prompt_version="v1", cache_path=cache)
    systems = systems_of(cache, essays)
    assert ev.evaluate(essays, systems, n_boot=10)["bootstrap"]["cluster_by_prompt"] is True
    assert ev.evaluate(essays, systems, n_boot=10, cluster_by_prompt=False)["bootstrap"]["cluster_by_prompt"] is False
    unique = [e.model_copy(update={"prompt": f"u{i}", "prompt_id": ""}) for i, e in enumerate(essays)]
    unique = [Essay.model_validate({**e.model_dump(), "text_hash": e.text_hash, "prompt_id": ""}) for e in unique]
    assert (
        ev.evaluate(unique, ev.systems_from_cache(load_cache(cache), unique), n_boot=10)["bootstrap"][
            "cluster_by_prompt"
        ]
        is False
    )


# --- 8. stability alignment --------------------------------------------------------------------------


def test_stability_aligns_runs_by_index_when_some_runs_fail(tmp_path):
    essays = make_essays(6, n_prompts=3, seed=11, split="test", prefix="t")
    index = {e.text: i for i, e in enumerate(essays)}
    state = {"n": 0}

    class G:
        def grade(self, *, task_type, prompt, text, min_words, seed=0):
            run = state["n"] // 6
            state["n"] += 1
            if run == 1 + index[text] % 2:  # each essay fails exactly one of runs 1 and 2
                raise RuntimeError("fail")
            return Feedback(band=[5.0, 6.0, 7.0][run], criteria={}, summary="s")

    cache = tmp_path / "c.jsonl"
    collect(
        essays,
        G(),
        provider="g",
        model="m",
        prompt_version="v",
        cache_path=cache,
        runs=3,
        retry_failed=False,
        abort_after=0,
    )
    system = systems_of(cache, essays)[0]
    for runs in system.runs.values():
        assert set(runs.values()) <= {5.0, 6.0, 7.0}
        assert all({0: 5.0, 1: 6.0, 2: 7.0}[i] == v for i, v in runs.items())
    stability = ws.stability(system.runs)
    assert stability["n_essays"] == 0 and stability["n_incomplete"] == 6
    assert stability["mean_pairwise_qwk"] is not None  # pairs use essays that have both runs
    assert ws.stability({"a": {0: 6.0, 2: 6.5}, "b": {0: 6.0, 2: 6.0}, "c": {0: 7.0, 2: 7.0}})["n_essays"] == 3
