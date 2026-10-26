"""Chronological, predict-before-update comparison on private response JSONL."""

import argparse
import hashlib
from collections import defaultdict
from dataclasses import asdict
from itertools import groupby
from pathlib import Path

from ml.data import ResponseRecord, read_jsonl, write_report
from ml.irt import fit_rasch
from ml.knowledge_tracing import fit_bkt
from ml.metrics import auc, brier, log_loss, reliability_bins
from ml.datasets.split import temporal_split


def summarize(predictions: list[dict]) -> dict:
    if not predictions:
        return {"count": 0, "correct": 0, "incorrect": 0, "auc_status": "empty", "metrics": {}}
    labels = [r["correct"] for r in predictions]
    return {
        "count": len(predictions),
        "correct": sum(labels),
        "incorrect": len(labels) - sum(labels),
        "auc_status": "available" if len(set(labels)) == 2 else "single_class",
        "metrics": {
            model: {
                "auc": auc(labels, [r[model] for r in predictions]),
                "brier": brier(labels, [r[model] for r in predictions]),
                "log_loss": log_loss(labels, [r[model] for r in predictions]),
            }
            for model in ("error_rate_baseline", "irt", "bkt", "blend")
        },
    }


def evaluate(records: list[ResponseRecord], train_fraction=0.75) -> dict:
    train, test, cutoff = temporal_split(records, train_fraction)
    irt, bkt = fit_rasch(train), fit_bkt(train)
    counts = defaultdict(lambda: [0, 0])
    for row in train:
        counts[(row.learner_id, row.skill_key)][0] += int(row.correct)
        counts[(row.learner_id, row.skill_key)][1] += 1
    train_learners = {r.learner_id for r in train}
    train_items = {r.item_key for r in train}
    predictions = []
    for _, bucket_iter in groupby(test, key=lambda r: r.answered_at):
        bucket = list(bucket_iter)
        # All simultaneous responses are predicted before any of them updates state.
        for row in bucket:
            successes, total = counts[(row.learner_id, row.skill_key)]
            irt_p = irt.probability(row.learner_id, row.skill, row.item_key)
            bkt_p = bkt.probability(row.learner_id, row.skill_key)
            supported = irt.item_support.get(row.item_key, 0) >= 10
            predictions.append(
                {
                    "response_id": row.response_id,
                    "correct": int(row.correct),
                    "skill": row.skill,
                    "new_learner": row.learner_id not in train_learners,
                    "new_item": row.item_key not in train_items,
                    "error_rate_baseline": (successes + 1) / (total + 2),
                    "irt": irt_p,
                    "bkt": bkt_p,
                    "blend": ((irt_p if supported else 0.5) + bkt_p) / 2,
                }
            )
        for row in bucket:
            irt.observe(row)
            bkt.observe(row)
            counts[(row.learner_id, row.skill_key)][0] += int(row.correct)
            counts[(row.learner_id, row.skill_key)][1] += 1
    labels = [r["correct"] for r in predictions]
    metrics = {}
    for model in ("error_rate_baseline", "irt", "bkt", "blend"):
        probabilities = [r[model] for r in predictions]
        metrics[model] = {
            "auc": auc(labels, probabilities),
            "brier": brier(labels, probabilities),
            "log_loss": log_loss(labels, probabilities),
            "reliability_bins": reliability_bins(labels, probabilities),
        }
    return {
        "schema_version": "adaptive-experiment.v1",
        "cutoff": cutoff.isoformat(),
        "train_count": len(train),
        "test_count": len(test),
        "holdout": summarize(predictions),
        "excluded_repeated_responses": len(records) - len(train) - len(test),
        "metrics": metrics,
        "predictions": predictions,
        "by_skill": {
            skill: summarize([r for r in predictions if r["skill"] == skill]) for skill in ("reading", "listening")
        },
        "cold_start": {
            field: {
                "unseen_at_cutoff": summarize([r for r in predictions if r[field]]),
                "seen_in_training": summarize([r for r in predictions if not r[field]]),
            }
            for field in ("new_learner", "new_item")
        },
        "settings": {
            "train_fraction": train_fraction,
            "irt_regularization": irt.regularization,
            "irt_online_learning_rate": 0.2,
            "blend_min_item_support": 10,
            "bkt_parameters": {k: asdict(v) for k, v in bkt.parameters.items()},
            "bkt_fitted_skills": sorted(bkt.fitted_skills),
        },
        "limitations": [
            "Single temporal holdout; null AUC means only one outcome class.",
            "Blend weights and support cutoff are pilot heuristics.",
            "Prediction quality does not establish learning gains; a user pilot is required.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("responses", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-fraction", type=float, default=0.75)
    args = parser.parse_args()
    report = evaluate(read_jsonl(args.responses, ResponseRecord), args.train_fraction)
    report["dataset_sha256"] = hashlib.sha256(args.responses.read_bytes()).hexdigest()
    write_report(args.output, report)


if __name__ == "__main__":
    main()
