"""E1 evaluator: one command -> markdown + JSON report comparing Writing graders.

    python -m ml.evaluate_writing --dataset essays.jsonl --manifest manifest.json \\
        --split test --cache ml/data/gemini.jsonl ml/data/qwen.jsonl \\
        --model-bundle ml/artifacts/writing-v1/writing_models.joblib \\
        --run-mock --prereg calibration/prereg-e1.md --out ml/reports/e1-test

Systems compared on the SAME essays: constant-mean and constant-mode baselines
(fit on the train split), the rule-based mock grader, trained Ridge / gradient
boosting, and every provider found in the cache files, plus the human-human
ceiling when the split has double-marked essays. Predictions of the first run
(run 0) are the primary result; further runs feed the stability section.
Failures are never dropped silently: coverage is a column, and metrics use the
essays covered by every system (n_common) so rows are directly comparable.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ml import writing_stats as ws
from ml.writing_data import CRITERIA, Essay, file_sha256, read_essays, split_fingerprints, verify_manifest
from ml.collect_writing import load_cache

REPORT_VERSION = "writing-eval.v1"
PROTECTED_SPLITS = ("test", "gold")
DEFAULT_THRESHOLDS = {"qwk_min": 0.6, "mae_max": 0.5, "within_0_5_min": 0.7, "coverage_min": 0.95}
PREREG_BLOCK = re.compile(r"```json prereg\s*(\{.*?\})\s*```", re.S)


class System:
    def __init__(self, name, kind, detail=None, id=None):
        # `name` is for display and can change when more systems are loaded; `id`
        # is the stable key used by pre-registrations (provider|model|prompt|seed).
        self.name, self.kind, self.detail = name, kind, detail or {}
        self.id = id or name
        self.pred: dict[str, dict[str, float]] = defaultdict(dict)  # target -> id -> band
        self.flags: dict[str, dict | None] = {}
        self.runs: dict[str, dict[int, float]] = {}
        self.attempted = 0
        self.failed = 0
        self.failure_reasons: Counter = Counter()


# ----------------------------------------------------------------- systems


def system_id(provider, model, prompt_version, seed) -> str:
    return f"{provider}|{model}|{prompt_version}|seed{seed}"


def constant_systems(train: list[Essay], fallback: list[Essay], ids: list[str]) -> list[System]:
    source, fit_on = (train, "train split") if train else (fallback, "evaluated essays (oracle constant)")
    labels = [e.overall for e in source]
    mean_value = sum(labels) / len(labels)
    mode_value = Counter(labels).most_common(1)[0][0]
    out = []
    for name, value in (("constant mean", mean_value), ("constant mode", mode_value)):
        s = System(name, "baseline", {"value": value, "fit_on": fit_on})
        s.pred["overall"] = {i: value for i in ids}
        for c in CRITERIA:
            cl = [e.criteria[c] for e in source if c in e.criteria]
            if cl:
                v = (sum(cl) / len(cl)) if "mean" in name else Counter(cl).most_common(1)[0][0]
                s.pred[c] = {i: v for i in ids}
        s.attempted = len(ids)
        out.append(s)
    return out


def systems_from_cache(records: dict[str, dict], essays: list[Essay], only: set[str] | None = None) -> list[System]:
    by_hash = {e.text_hash: e for e in essays}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for rec in records.values():
        if rec["essay_hash"] in by_hash and (not only or rec["provider"] in only):
            groups[(rec["provider"], rec["model"], rec["prompt_version"], rec["seed"])].append(rec)
    versions = Counter((p, m) for p, m, _, _ in groups)
    seeds = Counter((p, m, v) for p, m, v, _ in groups)
    systems = []
    for (provider, model, pv, seed), recs in sorted(groups.items()):
        name = f"{provider}:{model}" + (f"@{pv}" if versions[(provider, model)] > 1 else "")
        if seeds[(provider, model, pv)] > 1:
            name += f"#seed{seed}"
        kind = "rules" if provider == "mock" else "llm"
        s = System(
            name,
            kind,
            {"provider": provider, "model": model, "prompt_version": pv, "seed": seed},
            id=system_id(provider, model, pv, seed),
        )
        per_run: dict[str, dict[int, float]] = defaultdict(dict)
        for rec in recs:
            eid = by_hash[rec["essay_hash"]].id
            if rec["run"] == 0:
                s.attempted += 1
                if rec["ok"]:
                    s.pred["overall"][eid] = rec["band"]
                    for c, v in (rec.get("criteria") or {}).items():
                        s.pred[c][eid] = v
                    s.flags[eid] = rec.get("flags")
                else:
                    s.failed += 1
                    s.failure_reasons[str(rec.get("error"))[:60]] += 1
            if rec["ok"]:
                per_run[eid][rec["run"]] = rec["band"]
        s.runs = dict(per_run)  # essay id -> {run index: band}, aligned by index
        systems.append(s)
    return systems


def systems_from_bundle(path: Path, essays: list[Essay]) -> list[System]:
    from ml.train_writing import MODEL_NAMES, load_bundle, predict

    bundle = load_bundle(path)
    leaked = sorted(set(bundle["train_ids"]) & {e.id for e in essays})
    if leaked:
        raise ValueError(
            f"model was trained on {len(leaked)} of the evaluated essays; use --oof "
            "(out-of-fold predictions) for the train split instead"
        )
    out = []
    for name in MODEL_NAMES:
        s = System(
            name,
            "trained",
            {
                "feature_version": bundle["feature_version"],
                "n_train": bundle["n_train"],
                "train_fingerprint": bundle["train_fingerprint"][:12],
            },
        )
        for target, preds in predict(bundle, name, essays).items():
            for e, p in zip(essays, preds):
                s.pred[target][e.id] = p
        s.attempted = len(essays)
        out.append(s)
    return out


def systems_from_oof(path: Path, essays: list[Essay]) -> list[System]:
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = {e.id for e in essays}
    out = {}
    for row in report["oof"]:
        if row["id"] not in ids:
            continue
        for key, value in row.items():
            if ":" in key and value is not None:
                model, target = key.split(":", 1)
                s = out.setdefault(
                    model, System(f"{model} (grouped CV)", "trained", {"note": "out-of-fold, prompt-grouped"})
                )
                s.pred[target][row["id"]] = value
    for s in out.values():
        s.attempted = len(ids)
    return list(out.values())


# -------------------------------------------------------------- evaluation


def _aligned(essays_by_id, ids, labels_of, pred: dict):
    ids = [i for i in ids if i in pred and labels_of(essays_by_id[i]) is not None]
    return ids, [labels_of(essays_by_id[i]) for i in ids], [pred[i] for i in ids]


def _target_label(target):
    return (lambda e: e.overall) if target == "overall" else (lambda e: e.criteria.get(target))


def evaluate_system(
    s: System,
    essays_by_id: dict,
    common_ids: list[str],
    *,
    n_boot: int,
    seed: int,
    cluster_by_prompt: bool,
    ci_criteria: bool,
) -> dict:
    block: dict = {"name": s.name, "id": s.id, "kind": s.kind, "detail": s.detail}
    expected = len(essays_by_id)
    covered = len(s.pred["overall"])
    block["coverage"] = {
        "expected": expected,
        "covered": covered,
        "failed": s.failed,
        "missing": expected - covered - s.failed,
        "rate": covered / expected if expected else None,
        "failure_reasons": dict(s.failure_reasons),
    }
    # Metrics on every essay this system covered (not only the common subset), so
    # selective failures cannot hide behind the shared comparison set.
    own_ids, own_y, own_p = _aligned(essays_by_id, sorted(essays_by_id), _target_label("overall"), s.pred["overall"])
    if len(own_ids) >= 2:
        block["own_overall"] = {"n": len(own_ids), **ws.point_metrics(own_y, own_p)}
    targets = {}
    for target in ("overall", *CRITERIA):
        if target not in s.pred:
            continue
        ids, y, p = _aligned(essays_by_id, common_ids, _target_label(target), s.pred[target])
        if len(ids) < 2:
            continue
        clusters = [essays_by_id[i].prompt_id for i in ids] if cluster_by_prompt else None
        names = ws.POINT_METRICS if target == "overall" else ws._CI_FAST
        entry = {"n": len(ids), **ws.point_metrics(y, p), **ws.spread_stats(y, p)}
        if n_boot and (target == "overall" or ci_criteria):
            entry["ci95"] = ws.bootstrap_ci(y, p, names=names, n_boot=n_boot, seed=seed, clusters=clusters)
        if target == "overall":
            entry["confusion"] = ws.confusion_matrix(y, p)
        targets[target] = entry
    block["targets"] = targets
    if s.kind in ("llm", "rules") and s.runs:
        block["stability"] = ws.stability(s.runs)
    hits = [ws.cap_hit(s.flags.get(i)) for i in common_ids if i in s.flags]
    hits = [h for h in hits if h is not None]
    block["cap_hit_rate"] = (sum(hits) / len(hits)) if hits else None
    block["cap_hit_n"] = len(hits)
    return block


def human_ceiling(essays: list[Essay]) -> dict | None:
    pairs = []
    for e in essays:
        if len(e.rater_scores) >= 2:
            a, b = sorted(e.rater_scores, key=lambda r: r.rater_id)[:2]
            pairs.append((a, b))
    if len(pairs) < 2:
        return None
    out = {
        "name": "human vs human (ceiling)",
        "kind": "human",
        "detail": {"note": "rater 2 scored against rater 1 (first two raters by id)"},
        "coverage": {"expected": len(pairs), "covered": len(pairs), "failed": 0, "missing": 0, "rate": 1.0},
        "targets": {},
    }
    y = [a.overall for a, _ in pairs]
    p = [b.overall for _, b in pairs]
    out["targets"]["overall"] = {
        "n": len(pairs),
        **ws.point_metrics(y, p),
        **ws.spread_stats(y, p),
        "ci95": ws.bootstrap_ci(y, p, names=ws.POINT_METRICS, n_boot=1000, seed=0),
    }
    for c in CRITERIA:
        pc = [(a.criteria[c], b.criteria[c]) for a, b in pairs if c in a.criteria and c in b.criteria]
        if len(pc) >= 2:
            out["targets"][c] = {
                "n": len(pc),
                **ws.point_metrics([x for x, _ in pc], [z for _, z in pc]),
                **ws.spread_stats([x for x, _ in pc], [z for _, z in pc]),
            }
    return out


def evaluate(
    essays: list[Essay],
    systems: list[System],
    *,
    train_essays: list[Essay] | None = None,
    n_boot: int = 2000,
    seed: int = 0,
    reference: str | None = None,
    cluster_by_prompt: bool | None = None,
    ci_criteria: bool = False,
) -> dict:
    """`cluster_by_prompt=None` (default) resamples whole prompts whenever prompts
    repeat in the evaluated set, since essays on one prompt are not independent."""
    by_id = {e.id: e for e in essays}
    ids = sorted(by_id)
    all_systems = constant_systems(train_essays or [], essays, ids) + systems
    common = [i for i in ids if all(i in s.pred["overall"] for s in all_systems)]
    warnings = []
    if len(common) < len(ids):
        warnings.append(
            f"metrics use the {len(common)} essays covered by every system (of {len(ids)}); see each system's coverage"
        )
    if len(common) < 30:
        warnings.append(f"only {len(common)} common essays: confidence intervals are very wide")
    if cluster_by_prompt is None:
        cluster_by_prompt = len({by_id[i].prompt_id for i in common}) < len(common)
    blocks = [
        evaluate_system(
            s, by_id, common, n_boot=n_boot, seed=seed, cluster_by_prompt=cluster_by_prompt, ci_criteria=ci_criteria
        )
        for s in all_systems
    ]
    ceiling = human_ceiling([by_id[i] for i in ids])
    if ceiling:
        blocks.append(ceiling)
    paired = []
    ref = next((s for s in all_systems if reference in (s.name, s.id)), None) if reference else None
    if reference and ref is None:
        warnings.append(f"reference system {reference!r} not found")
    if ref is None:
        ref = next((s for s in all_systems if s.kind == "llm"), None)
    if ref is not None and len(common) >= 2:
        y = [by_id[i].overall for i in common]
        pr = [ref.pred["overall"][i] for i in common]
        clusters = [by_id[i].prompt_id for i in common] if cluster_by_prompt else None
        for other in all_systems:
            if other is ref:
                continue
            po = [other.pred["overall"][i] for i in common]
            paired.append(
                {
                    "a": ref.name,
                    "b": other.name,
                    "b_id": other.id,
                    "n": len(common),
                    "metrics": ws.paired_bootstrap_diff(y, pr, po, n_boot=n_boot, seed=seed, clusters=clusters),
                }
            )
    return {
        "schema_version": REPORT_VERSION,
        "systems": blocks,
        "paired_vs_reference": paired,
        "reference": ref.name if ref else None,
        "n_essays": len(ids),
        "n_common": len(common),
        "bootstrap": {"n_boot": n_boot, "seed": seed, "cluster_by_prompt": cluster_by_prompt},
        "warnings": warnings,
    }


# ---------------------------------------------------------- pre-registration


def parse_prereg(path: Path) -> dict:
    match = PREREG_BLOCK.search(Path(path).read_text(encoding="utf-8"))
    if not match:
        raise ValueError("pre-registration file has no ```json prereg block")
    return json.loads(match.group(1))


def check_protocol(
    prereg: dict,
    report: dict,
    split: str,
    *,
    dataset_sha256: str | None = None,
    fingerprints: dict[str, str] | None = None,
) -> list[str]:
    """Deviations from the frozen protocol. Works without a manifest: the dataset
    hash and per-split fingerprints are recomputed from the dataset itself."""
    deviations = []
    frozen_sha = prereg.get("dataset_sha256")
    if frozen_sha and dataset_sha256 and frozen_sha != dataset_sha256:
        deviations.append("dataset file hash differs from the pre-registered one")
    frozen = prereg.get("split_fingerprints", {})
    if split in frozen:
        if (fingerprints or {}).get(split) != frozen[split]:
            deviations.append(f"split {split!r} fingerprint differs from the pre-registered one")
    elif split in PROTECTED_SPLITS:
        deviations.append(f"split {split!r} has no pre-registered fingerprint")
    allowed = {
        m.get("id") or system_id(m["provider"], m["model"], m["prompt_version"], m.get("seed", 0))
        for m in prereg.get("systems", [])
    }
    for block in report["systems"]:
        if block["kind"] in ("llm", "rules") and block["id"] not in allowed:
            d = block["detail"]
            deviations.append(
                f"system {block['name']} (prompt {d['prompt_version']}, seed {d['seed']}) is not pre-registered"
            )
    return deviations


def threshold_verdict(prereg: dict, report: dict) -> dict:
    """Pre-registered pass/fail for the primary system. The primary is matched by
    its stable id and a missing primary is an error, never a silent skip."""
    primary = prereg.get("primary_id") or prereg.get("primary_system")
    if not primary:
        raise ValueError("the pre-registration names no primary system (primary_id)")
    th = {**DEFAULT_THRESHOLDS, **prereg.get("thresholds", {})}
    block = next((b for b in report["systems"] if primary in (b.get("id"), b["name"])), None)
    if block is None:
        raise ValueError(f"pre-registered primary system {primary!r} is not in the evaluated systems")
    if "overall" not in block["targets"]:
        raise ValueError(f"primary system {primary!r} has too few scored essays to evaluate")
    t = block["targets"]["overall"]
    ci = t.get("ci95", {})
    q_lo = (ci.get("qwk") or {}).get("lo")
    cov = block["coverage"]
    verdict = {
        "primary_id": block["id"],
        "primary_system": block["name"],
        "thresholds": th,
        "coverage": {"covered": cov["covered"], "expected": cov["expected"], "rate": cov["rate"]},
        "n_scored_common": t["n"],
        "coverage_ok": cov["rate"] is not None and cov["rate"] >= th["coverage_min"],
        "qwk_point_ok": t["qwk"] is not None and t["qwk"] >= th["qwk_min"],
        "qwk_ci_lower_ok": q_lo is not None and q_lo >= th["qwk_min"],
        "mae_ok": t["mae"] <= th["mae_max"],
        "within_0_5_ok": t["within_0_5"] >= th["within_0_5_min"],
    }
    verdict["all_ok"] = all(verdict[k] for k in ("coverage_ok", "qwk_point_ok", "mae_ok", "within_0_5_ok"))
    return verdict


def render_prereg(
    *, dataset_sha256, fingerprints: dict[str, str], systems: list[dict], primary: str | None, thresholds=None
) -> str:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_sha256": dataset_sha256,
        "split_fingerprints": fingerprints,
        "systems": systems,
        "primary_system": next((m["name"] for m in systems if m["id"] == primary), None),
        "primary_id": primary,
        "thresholds": thresholds or DEFAULT_THRESHOLDS,
    }
    template = Path(__file__).resolve().parents[1] / "calibration" / "PREREGISTRATION_TEMPLATE.md"
    head = template.read_text(encoding="utf-8") if template.exists() else "# E1 pre-registration\n"
    return head.replace("<<FROZEN_BLOCK>>", "```json prereg\n" + json.dumps(payload, indent=2) + "\n```")


# ------------------------------------------------------------------ render


def _f(v, digits=3):
    return "n/a" if v is None else f"{v:.{digits}f}"


def _ci(t, name, digits=3):
    c = (t.get("ci95") or {}).get(name)
    return (
        f"{_f(t.get(name), digits)} [{_f(c['lo'], digits)}, {_f(c['hi'], digits)}]"
        if c and c["lo"] is not None
        else _f(t.get(name), digits)
    )


def render_markdown(report: dict, meta: dict) -> str:
    lines = [
        "# E1 Writing accuracy report",
        "",
        f"- split: `{meta['split']}`; essays: {report['n_essays']}; common to all systems: {report['n_common']}",
        f"- dataset sha256: `{meta.get('dataset_sha256')}`",
        f"- generated: {meta['generated_at']}; bootstrap: {report['bootstrap']['n_boot']} resamples, "
        f"seed {report['bootstrap']['seed']}, cluster_by_prompt={report['bootstrap']['cluster_by_prompt']}",
    ]
    if meta["split"] == "dev":
        lines.append("- **DEV SET: the prompt was tuned on these essays. Do not report as a result.**")
    for w in report["warnings"] + meta.get("protocol_deviations", []):
        lines.append(f"- WARNING: {w}")
    lines += [
        "",
        "## Overall band (95% bootstrap CI)",
        "",
        "| System | n | Coverage | QWK | MAE | within 0.5 | within 1.0 | Pearson | Bias | SD pred/label | Mode share | Cap hit |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for b in report["systems"]:
        t = b["targets"].get("overall")
        cov = b["coverage"]
        cov_s = f"{cov['covered']}/{cov['expected']}" + (f" ({cov['failed']} failed)" if cov["failed"] else "")
        if not t:
            lines.append(f"| {b['name']} | 0 | {cov_s} | | | | | | | | | |")
            continue
        sdr = f"{_f(t['sd_prediction'], 2)}/{_f(t['sd_label'], 2)}"
        lines.append(
            f"| {b['name']} | {t['n']} | {cov_s} | {_ci(t, 'qwk')} | {_ci(t, 'mae')} | "
            f"{_ci(t, 'within_0_5', 2)} | {_f(t['within_1_0'], 2)} | {_f(t['pearson'])} | "
            f"{_f(t['bias'], 2)} | {sdr} | {_f(t['mode_share'], 2)} @ {t['mode_value']} | "
            f"{_f(b.get('cap_hit_rate'), 2)} |"
        )
    lines += [
        "",
        "A constant predictor has QWK 0 and Pearson n/a but can still have a respectable MAE; "
        "read QWK, SD ratio and mode share together.",
        "",
    ]
    crit = [b for b in report["systems"] if any(c in b["targets"] for c in CRITERIA)]
    if crit:
        lines += [
            "## Per-criterion QWK / MAE",
            "",
            "| System | " + " | ".join(CRITERIA) + " |",
            "|---|" + "---|" * len(CRITERIA),
        ]
        for b in crit:
            cells = []
            for c in CRITERIA:
                t = b["targets"].get(c)
                cells.append(f"{_f(t['qwk'])} / {_f(t['mae'], 2)} (n={t['n']})" if t else "n/a")
            lines.append(f"| {b['name']} | " + " | ".join(cells) + " |")
        lines.append("")
    stab = [b for b in report["systems"] if b.get("stability")]
    if stab:
        lines += [
            "## Run-to-run stability",
            "",
            "| System | runs | essays | mean SD | max SD | essays that flip | ICC(2,1) | mean pairwise QWK |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for b in stab:
            s = b["stability"]
            if "icc_2_1" not in s:
                lines.append(f"| {b['name']} | {s['n_runs']} | {s['n_essays']} | {s['note']} | | | | |")
                continue
            lines.append(
                f"| {b['name']} | {s['n_runs']} | {s['n_essays']} | {_f(s['mean_within_essay_sd'])} | "
                f"{_f(s['max_within_essay_sd'])} | {_f(s['pct_essays_any_flip'], 2)} | "
                f"{_f(s['icc_2_1'])} | {_f(s['mean_pairwise_qwk'])} |"
            )
        lines.append("")
    if report["paired_vs_reference"]:
        lines += [
            f"## Paired bootstrap vs `{report['reference']}` (A minus B, same essays)",
            "",
            "| B | n | dQWK [CI] | p | dMAE [CI] | p |",
            "|---|---|---|---|---|---|",
        ]
        for p in report["paired_vs_reference"]:
            q, m = p["metrics"]["qwk"], p["metrics"]["mae"]
            lines.append(
                f"| {p['b']} | {p['n']} | {_f(q['diff'])} [{_f(q['lo'])}, {_f(q['hi'])}] | "
                f"{_f(q['p_two_sided'], 3)} | {_f(m['diff'])} [{_f(m['lo'])}, {_f(m['hi'])}] | "
                f"{_f(m['p_two_sided'], 3)} |"
            )
        lines.append("")
    if meta.get("verdict"):
        lines += ["## Pre-registered thresholds", "", "```json", json.dumps(meta["verdict"], indent=2), "```", ""]
    lines += ["## Confusion matrices (rows = human, columns = system)", ""]
    for b in report["systems"]:
        c = (b["targets"].get("overall") or {}).get("confusion")
        if not c or b["kind"] in ("human",):
            continue
        lines += [
            f"**{b['name']}**",
            "",
            "| human \\ system | " + " | ".join(str(x) for x in c["labels"]) + " |",
            "|---|" + "---|" * len(c["labels"]),
        ]
        for lab, row in zip(c["labels"], c["matrix"]):
            lines.append(f"| {lab} | " + " | ".join(str(x) for x in row) + " |")
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="split manifest; verified against the dataset")
    parser.add_argument("--split", required=True, choices=["dev", "train", "test", "gold"])
    parser.add_argument("--cache", type=Path, nargs="*", default=[], help="collector cache file(s)")
    parser.add_argument("--only", nargs="*", help="restrict cache systems to these providers")
    parser.add_argument("--model-bundle", type=Path, help="writing_models.joblib (not trained on this split)")
    parser.add_argument("--oof", type=Path, help="training_report.json: grouped-CV predictions (split=train)")
    parser.add_argument("--run-mock", action="store_true", help="grade the split with the free rule-based mock")
    parser.add_argument("--mock-cache", type=Path, help="cache file for --run-mock (default: <out>-mock-cache.jsonl)")
    parser.add_argument("--reference", help="system name for paired comparisons (default: first LLM)")
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--cluster-by-prompt",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="cluster bootstrap by prompt (default: on whenever prompts repeat; --no-cluster-by-prompt disables)",
    )
    parser.add_argument("--ci-criteria", action="store_true", help="also bootstrap per-criterion QWK/MAE")
    parser.add_argument("--prereg", type=Path, help="frozen protocol (required for test/gold)")
    parser.add_argument(
        "--allow-unregistered",
        action="store_true",
        help="evaluate test/gold without a pre-registration (recorded in the report)",
    )
    parser.add_argument("--write-prereg", type=Path, help="write a pre-registration file from the cache and exit")
    parser.add_argument("--primary", help="primary system name for --write-prereg")
    parser.add_argument("--out", type=Path, help="output prefix: writes <out>.md and <out>.json")
    args = parser.parse_args(argv)

    all_essays = read_essays(args.dataset)
    dataset_sha = file_sha256(args.dataset)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else None
    if manifest:
        problems = verify_manifest(all_essays, manifest)
        if problems:
            raise SystemExit("dataset does not match its manifest:\n  " + "\n  ".join(problems))
    essays = [e for e in all_essays if e.split == args.split]
    if not essays:
        raise SystemExit(f"no essays in split {args.split!r}")

    records: dict = {}
    for path in args.cache:
        records.update(load_cache(path))
    if args.run_mock:
        from ml import graders
        from ml.collect_writing import collect

        mock_cache = args.mock_cache or (
            Path(str(args.out) + "-mock-cache.jsonl") if args.out else Path("mock-cache.jsonl")
        )
        collect(
            essays,
            graders.make_grader("mock"),
            provider="mock",
            model=graders.model_name("mock"),
            prompt_version=graders.prompt_version(),
            cache_path=mock_cache,
        )
        records.update(load_cache(mock_cache))
    systems = systems_from_cache(records, essays, set(args.only) if args.only else None)
    if args.model_bundle:
        systems += systems_from_bundle(args.model_bundle, essays)
    if args.oof:
        if args.split != "train":
            raise SystemExit("--oof only applies to --split train")
        systems += systems_from_oof(args.oof, essays)

    if args.write_prereg:
        reg = [
            {
                "provider": s.detail["provider"],
                "model": s.detail["model"],
                "prompt_version": s.detail["prompt_version"],
                "seed": s.detail["seed"],
                "id": s.id,
                "name": s.name,
            }
            for s in systems
            if s.kind in ("llm", "rules")
        ]
        primary = next((m["id"] for m in reg if args.primary in (m["id"], m["name"])), None)
        if primary is None:
            raise SystemExit(
                f"--primary {args.primary!r} must name one of the collected systems: "
                + ", ".join(m["name"] for m in reg)
            )
        text = render_prereg(
            dataset_sha256=dataset_sha, fingerprints=split_fingerprints(all_essays), systems=reg, primary=primary
        )
        args.write_prereg.parent.mkdir(parents=True, exist_ok=True)
        with args.write_prereg.open("x", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.write_prereg}; sha256 {hashlib.sha256(text.encode()).hexdigest()}")
        return 0

    prereg = None
    if args.split in PROTECTED_SPLITS:
        if args.prereg:
            prereg = parse_prereg(args.prereg)
        elif not args.allow_unregistered:
            raise SystemExit(
                f"split {args.split!r} is protected: freeze the protocol first "
                "(--write-prereg, then --prereg) or pass --allow-unregistered"
            )
    train_essays = [e for e in all_essays if e.split == "train"]
    report = evaluate(
        essays,
        systems,
        train_essays=train_essays,
        n_boot=args.n_boot,
        seed=args.seed,
        reference=args.reference,
        cluster_by_prompt=args.cluster_by_prompt,
        ci_criteria=args.ci_criteria,
    )
    meta = {
        "split": args.split,
        "dataset_sha256": dataset_sha,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(sys.argv[1:]) if argv is None else " ".join(argv),
        "protocol_deviations": [],
        "prereg_sha256": None,
        "verdict": None,
    }
    if args.split in PROTECTED_SPLITS and prereg is None:
        meta["protocol_deviations"].append("evaluated WITHOUT a pre-registered protocol")
    if prereg is not None:
        meta["prereg_sha256"] = file_sha256(args.prereg)
        meta["protocol_deviations"] += check_protocol(
            prereg,
            report,
            args.split,
            dataset_sha256=dataset_sha,
            fingerprints=split_fingerprints(all_essays),
        )
        try:
            meta["verdict"] = threshold_verdict(prereg, report)
        except ValueError as exc:
            raise SystemExit(f"cannot compute the pre-registered verdict: {exc}") from None
    report["meta"] = meta
    markdown = render_markdown(report, meta)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        Path(str(args.out) + ".md").write_text(markdown, encoding="utf-8")
        Path(str(args.out) + ".json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.out}.md and {args.out}.json")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
