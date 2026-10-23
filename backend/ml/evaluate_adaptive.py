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
from ml.metrics import auc, brier
from ml.datasets.split import temporal_split


def evaluate(records: list[ResponseRecord], train_fraction=0.75) -> dict:
    train, test, cutoff = temporal_split(records, train_fraction)
    irt, bkt = fit_rasch(train), fit_bkt(train)
    counts = defaultdict(lambda: [0, 0])
    for row in train:
        counts[(row.learner_id, row.skill_key)][0] += int(row.correct)
        counts[(row.learner_id, row.skill_key)][1] += 1
    predictions = []
    for _, bucket_iter in groupby(test, key=lambda r: r.answered_at):
        bucket = list(bucket_iter)
        # All simultaneous responses are predicted before any of them updates state.
        for row in bucket:
            successes, total = counts[(row.learner_id, row.skill_key)]
            irt_p = irt.probability(row.learner_id, row.skill, row.item_key)
            bkt_p = bkt.probability(row.learner_id, row.skill_key)
            supported = irt.item_support.get(row.item_key, 0) >= 10
            predictions.append({
                "response_id": row.response_id, "correct": int(row.correct),
                "error_rate_baseline": (successes + 1) / (total + 2),
                "irt": irt_p, "bkt": bkt_p,
                "blend": ((irt_p if supported else 0.5) + bkt_p) / 2,
            })
        for row in bucket:
            irt.observe(row)
            bkt.observe(row)
            counts[(row.learner_id, row.skill_key)][0] += int(row.correct)
            counts[(row.learner_id, row.skill_key)][1] += 1
    labels = [r["correct"] for r in predictions]
    metrics = {}
    for model in ("error_rate_baseline", "irt", "bkt", "blend"):
        probabilities = [r[model] for r in predictions]
        metrics[model] = {"auc": auc(labels, probabilities),
                          "brier": brier(labels, probabilities)}
    return {
        "schema_version": "adaptive-experiment.v1", "cutoff": cutoff.isoformat(),
        "train_count": len(train), "test_count": len(test),
        "excluded_repeated_responses": len(records) - len(train) - len(test),
        "metrics": metrics, "predictions": predictions,
        "settings": {"train_fraction": train_fraction, "irt_regularization": irt.regularization,
                     "irt_online_learning_rate": 0.2, "blend_min_item_support": 10,
                     "bkt_parameters": {k: asdict(v) for k, v in bkt.parameters.items()},
                     "bkt_fitted_skills": sorted(bkt.fitted_skills)},
        "limitations": ["Single temporal holdout; null AUC means only one outcome class.",
                        "Blend weights and support cutoff are pilot heuristics.",
                        "Prediction quality does not establish learning gains; a user pilot is required."],
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
