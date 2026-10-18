"""Check an exported response.v1 JSONL before running adaptive experiments.

Run from backend:
python -m ml.datasets.readiness ml/data/responses.jsonl --output ml/reports/readiness.json

Exit codes: 0 = pilot can run (inspect warnings); 2 = blocked. No database access.
Thresholds describe current pilot code, not proof of statistical sufficiency.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from ml.data import ResponseRecord
from ml.datasets.split import first_responses, temporal_split


def counts(rows):
    correct = sum(r.correct for r in rows)
    return {"responses": len(rows), "learners": len({r.learner_id for r in rows}),
            "items": len({r.item_key for r in rows}), "correct": correct,
            "incorrect": len(rows) - correct}


def assess(records: list[ResponseRecord], train_fraction=0.75) -> dict:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be inside (0, 1)")
    blockers, warnings = [], []
    duplicates = len(records) - len({r.response_id for r in records})
    if duplicates:
        blockers.append("Duplicate response IDs: rebuild the export without duplicated records.")
    types = defaultdict(set)
    for row in records:
        types[row.item_key].add(row.question_type)
    if any(len(values) > 1 for values in types.values()):
        blockers.append("A versioned item has conflicting question types: fix the source mapping.")
    unique = first_responses(records)
    repeats = len(records) - len(unique)
    if repeats:
        warnings.append("Repeated learner/item responses will be excluded before splitting.")
    legacy = sum(r.content_version == "legacy" for r in unique)
    if legacy:
        warnings.append("Legacy content versions cannot establish historical item consistency.")
    train, test, cutoff = [], [], None
    try:
        train, test, cutoff = temporal_split(records, train_fraction)
    except ValueError as exc:
        blockers.append(str(exc))
    auc_available = len({r.correct for r in test}) == 2
    if test and not auc_available:
        blockers.append("Holdout has only one outcome class: collect correct and incorrect answers for AUC.")
    if train and len({r.correct for r in train}) < 2:
        warnings.append("Training has only one outcome class; collect more varied responses.")
    item_train, type_train = defaultdict(list), defaultdict(list)
    for row in train:
        item_train[row.item_key].append(row)
        type_train[row.skill_key].append(row)
    item_all, type_all = defaultdict(list), defaultdict(list)
    for row in unique:
        item_all[row.item_key].append(row)
        type_all[row.skill_key].append(row)
    all_items = {r.item_key: r for r in unique}
    all_types = {r.skill_key: r for r in unique}
    items = [{"item_id": row.item_id, "skill": row.skill, "content_version": row.content_version,
              "first_responses": counts(item_all[key]),
              "train": counts(item_train[key]), "meets_pilot_support": len(item_train[key]) >= 10}
             for key, row in sorted(all_items.items())]
    question_types = [{"skill": row.skill, "question_type": row.question_type,
                       "first_responses": counts(type_all[key]), "train": counts(type_train[key]),
                       "meets_bkt_fit_threshold": len(type_train[key]) >= 10 and len({r.learner_id for r in type_train[key]}) >= 2}
                      for key, row in sorted(all_types.items())]
    if any(not item["meets_pilot_support"] for item in items):
        warnings.append("Some items have fewer than 10 training responses; the blend uses a neutral IRT prior for them.")
    if any(not item["meets_bkt_fit_threshold"] for item in question_types):
        warnings.append("Some question types lack 10 training responses from 2 learners; BKT uses default parameters.")
    train_users = {r.learner_id for r in train}
    cold_users = len({r.learner_id for r in test} - train_users)
    cold_items = len({r.item_key for r in test} - set(item_train))
    if cold_users or cold_items:
        warnings.append("Holdout contains unseen learners or items; report cold-start performance separately.")
    by_skill = {}
    for skill in ("reading", "listening"):
        subset = [r for r in unique if r.skill == skill]
        held = [r for r in test if r.skill == skill]
        by_skill[skill] = {**counts(subset), "holdout": counts(held),
                           "holdout_auc_available": len({r.correct for r in held}) == 2}
        if not subset:
            warnings.append(f"No {skill} data: this export cannot evaluate that skill.")
        elif test and len({r.correct for r in held}) < 2:
            warnings.append(f"No usable per-skill AUC for {skill} in this holdout.")
    return {
        "schema_version": "response-readiness.v1",
        "status": "blocked" if blockers else "pilot_with_warnings" if warnings else "pilot_ready",
        "can_run_auc_comparison": not blockers,
        "blockers": blockers, "warnings": warnings,
        "raw": counts(records), "first_responses": counts(unique),
        "duplicate_response_ids": duplicates, "excluded_repeats": repeats, "legacy_responses": legacy,
        "split": {"train_fraction": train_fraction, "cutoff": cutoff.isoformat() if cutoff else None,
                  "train": counts(train), "holdout": counts(test), "auc_available": auc_available,
                  "unseen_holdout_learners": cold_users, "unseen_holdout_items": cold_items},
        "by_skill": by_skill, "items": items, "question_types": question_types,
        "limitations": ["Pilot thresholds are implementation defaults, not evidence of sufficient sample size.",
                        "Passing this check does not demonstrate prediction quality or learning gains.",
                        "Submission timestamps do not measure per-question response order.",
                        "response.v1 does not contain mode or consent information; inspect export metadata and study records."],
    }


def inspect_file(source: Path, train_fraction=0.75):
    payload = source.read_bytes()
    records, invalid_lines = [], []
    for number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = ResponseRecord.model_validate_json(line)
            if any(not getattr(row, field).strip() for field in ("response_id", "learner_id", "item_id", "content_version", "question_type")):
                raise ValueError("Blank identifier")
            records.append(row)
        except ValueError:
            invalid_lines.append(number)
    report = assess(records, train_fraction)
    report.update(dataset_sha256=hashlib.sha256(payload).hexdigest(), invalid_lines=invalid_lines)
    if invalid_lines:
        report["status"] = "blocked"
        report["can_run_auc_comparison"] = False
        report["blockers"].append("Invalid records exist; fix the listed lines before using the dataset. Counts cover valid rows only.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("responses", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-fraction", type=float, default=0.75)
    args = parser.parse_args()
    try:
        report = inspect_file(args.responses, args.train_fraction)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
    except (OSError, ValueError) as exc:
        parser.error(f"Cannot inspect dataset or create report ({type(exc).__name__}). Check paths, encoding, split and existing output.")
    print(json.dumps({key: report[key] for key in ("status", "raw", "first_responses", "blockers", "warnings")}))
    return 0 if report["can_run_auc_comparison"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
