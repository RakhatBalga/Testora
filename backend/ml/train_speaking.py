"""Compare baseline, linear regression and gradient boosting on held-out speakers."""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from ml.data import Record, write_report
from ml.metrics import half_band, mae, qwk, band_agreement
from ml.speech_features import FEATURE_NAMES, FEATURE_VERSION
from pydantic import Field


class FeatureSample(Record):
    sample_id: str = Field(min_length=1)
    speaker_id: str = Field(min_length=1)
    expert_band: float = Field(ge=0, le=9, multiple_of=0.5)
    llm_band: float | None = Field(default=None, ge=0, le=9)
    features: dict[str, float | None]


def score_summary(actual, predicted):
    return {"mae": mae(actual, predicted),
            "qwk": qwk(actual, [half_band(v) for v in predicted]),
            "within_half_band": band_agreement(actual, predicted),
            "within_one_band": band_agreement(actual, predicted, 1.0),
            "mean_signed_error": sum(p - a for a, p in zip(actual, predicted)) / len(actual),
            "rmse": math.sqrt(sum((p - a) ** 2 for a, p in zip(actual, predicted)) / len(actual))}


def train_compare(rows: list[dict], *, seed=42, test_size=0.25, artifacts: Path | None = None):
    import joblib
    import numpy as np
    import sklearn
    from sklearn.dummy import DummyRegressor
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    samples = [FeatureSample.model_validate({k: r[k] for k in FeatureSample.model_fields if k in r}) for r in rows]
    samples.sort(key=lambda r: (r.speaker_id, r.sample_id))
    if len({r.sample_id for r in samples}) != len(samples):
        raise ValueError("Duplicate samples would bias evaluation")
    if len({r.speaker_id for r in samples}) < 4:
        raise ValueError("At least four distinct speakers are required for a pilot split")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between zero and one")
    if any(set(r.features) != set(FEATURE_NAMES) for r in samples):
        raise ValueError("Feature schema differs from fluency.v1")
    x = np.array([[r.features[name] if r.features[name] is not None else np.nan for name in FEATURE_NAMES] for r in samples])
    y = np.array([r.expert_band for r in samples])
    groups = [r.speaker_id for r in samples]
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train, test = next(splitter.split(x, y, groups))
    models = {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "linear_regression": LinearRegression(),
        "gradient_boosting": GradientBoostingRegressor(n_estimators=80, max_depth=2, random_state=seed),
    }
    scores = {}
    if artifacts:
        artifacts.mkdir(parents=True, exist_ok=False)
    for name, estimator in models.items():
        # All preprocessing is fit only on training speakers.
        pipeline = make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                                 StandardScaler(), estimator)
        pipeline.fit(x[train], y[train])
        predicted = np.clip(pipeline.predict(x[test]), 0, 9).tolist()
        scores[name] = {
            **score_summary(y[test].tolist(), predicted),
            "predictions": [{"sample_id": samples[i].sample_id, "predicted_band": p,
                             "expert_band": samples[i].expert_band} for i, p in zip(test, predicted)],
        }
        if artifacts:
            joblib.dump({"pipeline": pipeline, "feature_names": FEATURE_NAMES,
                         "feature_version": FEATURE_VERSION, "sklearn_version": sklearn.__version__},
                        artifacts / f"{name}.joblib")
    # Compare only on exactly the same held-out recordings, never a convenient subset.
    llm = [samples[i].llm_band for i in test]
    scores["llm_transcript"] = (
        score_summary(y[test].tolist(), llm)
        if all(v is not None for v in llm) else {"status": "missing_held_out_scores"}
    )
    scores["llm_transcript"]["coverage"] = {
        "available": sum(v is not None for v in llm), "required": len(llm)}
    if all(v is not None for v in llm):
        scores["llm_transcript"]["predictions"] = [
            {"sample_id": samples[i].sample_id, "expert_band": samples[i].expert_band,
             "predicted_band": p} for i, p in zip(test, llm)]
    return {
        "schema_version": "speaking-experiment.v1", "feature_version": FEATURE_VERSION,
        "seed": seed, "test_size": test_size, "sklearn_version": sklearn.__version__,
        "train_speakers": sorted({groups[i] for i in train}), "test_speakers": sorted({groups[i] for i in test}),
        "train_count": len(train), "test_count": len(test), "models": scores,
        "split_samples": {split: [samples[i].sample_id for i in indices]
                          for split, indices in (("train", train), ("holdout", test))},
        "band_distribution": {split: dict(sorted(Counter(str(samples[i].expert_band) for i in indices).items()))
                              for split, indices in (("train", train), ("holdout", test))},
        "feature_missingness": {
            split: {name: {"missing": sum(samples[i].features[name] is None for i in indices),
                           "total": len(indices)} for name in FEATURE_NAMES}
            for split, indices in (("train", train), ("holdout", test))},
        "limitations": ["Single pilot split; no confidence intervals or tuning.",
                        "ASR fluency proxies do not establish pronunciation or IELTS validity.",
                        "QWK is null if chance disagreement is zero."],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("--model", required=True, help="Whisper model name in the ASR comparison")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.25)
    args = parser.parse_args(argv)
    source = json.loads(args.benchmark.read_text(encoding="utf-8"))
    if source.get("schema_version") != "asr-comparison.v1":
        raise ValueError("Expected asr-comparison.v1")
    runs = [r for r in source["runs"] if r["config"]["model"] == args.model]
    if len(runs) != 1 or runs[0].get("feature_version") != FEATURE_VERSION:
        raise ValueError("Select one compatible ASR run")
    report = train_compare(runs[0]["samples"], seed=args.seed, test_size=args.test_size, artifacts=args.artifacts)
    report.update(asr_model=args.model, benchmark_sha256=hashlib.sha256(args.benchmark.read_bytes()).hexdigest())
    write_report(args.output, report)


if __name__ == "__main__":
    main()
