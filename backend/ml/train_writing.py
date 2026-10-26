"""Train Ridge and gradient boosting on text features for IELTS Writing bands.

    python -m ml.train_writing --dataset essays.jsonl --out-dir ml/artifacts/writing-v1

Trains only on the `train` split (never test/gold). Cross-validation is grouped
by prompt (GroupKFold), so no prompt appears on both sides of a fold. Out-of-fold
predictions and CV metrics go to training_report.json; the final models (fit on
the whole train split) go to writing_models.joblib with metadata. Existing
output is never overwritten (same pattern as ml.train_speaking).
"""

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from ml.data import write_report
from ml.writing_data import CRITERIA, Essay, read_essays, file_sha256

# _dense/_texts live in writing_features so pickles never reference __main__.
from ml.writing_features import FEATURE_VERSION, dense_matrix as _dense, texts_of as _texts
from ml.writing_stats import point_metrics

MODEL_NAMES = ("ridge", "gbm")
MIN_CRITERION_ROWS = 30
BUNDLE_VERSION = "writing-models.v1"


def build_pipeline(name: str, seed: int):
    from sklearn.decomposition import TruncatedSVD
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.preprocessing import FunctionTransformer, StandardScaler

    dense = FunctionTransformer(_dense)
    tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=20000)
    texts = FunctionTransformer(_texts)
    if name == "ridge":
        union = FeatureUnion(
            [
                ("dense", Pipeline([("f", dense), ("scale", StandardScaler())])),
                ("tfidf", Pipeline([("t", texts), ("v", tfidf)])),
            ]
        )
        return Pipeline([("features", union), ("model", RidgeCV(alphas=(0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0)))])
    if name == "gbm":
        union = FeatureUnion(
            [
                ("dense", dense),
                (
                    "svd",
                    Pipeline([("t", texts), ("v", tfidf), ("s", TruncatedSVD(n_components=20, random_state=seed))]),
                ),
            ]
        )
        return Pipeline(
            [
                ("features", union),
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=seed
                    ),
                ),
            ]
        )
    raise ValueError(f"unknown model {name!r}")


def _x(essays):
    return [(e.task_type, e.text) for e in essays]


def _label(essay: Essay, target: str):
    return essay.overall if target == "overall" else essay.criteria.get(target)


def targets_for(essays: list[Essay]) -> list[str]:
    out = ["overall"]
    out += [c for c in CRITERIA if sum(c in e.criteria for e in essays) >= MIN_CRITERION_ROWS]
    return out


def _clip(values):
    return [min(9.0, max(0.0, float(v))) for v in values]


def predict(bundle: dict, model: str, essays: list[Essay]) -> dict[str, list[float]]:
    """Predictions per target from a loaded bundle (clipped to 0..9)."""
    X = _x(essays)
    return {t: _clip(p.predict(X)) for t, p in bundle["models"][model].items()}


def load_bundle(path: Path) -> dict:
    import joblib

    bundle = joblib.load(path)
    if bundle.get("bundle_version") != BUNDLE_VERSION:
        raise ValueError("not a writing-models.v1 bundle")
    if bundle["feature_version"] != FEATURE_VERSION:
        raise ValueError("feature definitions changed since this model was trained")
    return bundle


def train(
    essays: list[Essay],
    *,
    seed: int = 42,
    folds: int = 5,
    out_dir: Path | None = None,
    dataset_sha256: str | None = None,
) -> dict:
    import joblib
    import numpy as np
    import sklearn
    from sklearn.model_selection import GroupKFold

    rows = [e for e in essays if e.split == "train"]
    if any(e.split in ("test", "gold") for e in rows):
        raise ValueError("test/gold essays must never be used for training")
    groups = [e.prompt_id for e in rows]
    n_groups = len(set(groups))
    if n_groups < 2 or len(rows) < 10:
        raise ValueError("need >= 10 train essays from >= 2 distinct prompts")
    n_folds = min(folds, n_groups)
    targets = targets_for(rows)
    report: dict = {
        "schema_version": "writing-training.v1",
        "feature_version": FEATURE_VERSION,
        "seed": seed,
        "sklearn_version": sklearn.__version__,
        "n_train": len(rows),
        "n_prompts": n_groups,
        "folds": n_folds,
        "cv": "GroupKFold grouped by prompt_id",
        "targets": targets,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_sha256": dataset_sha256,
        "models": {},
        "oof": [],
        "limitations": [
            "Surface features only; spelling/agreement errors are proxied, not measured.",
            "Public labels are single non-certified raters (noisy).",
        ],
    }
    X = _x(rows)
    folds_idx = list(GroupKFold(n_splits=n_folds).split(np.zeros(len(rows)), groups=groups))
    oof: dict[str, dict[str, list]] = {
        n: {t: [None] * len(rows) for t in targets} for n in (*MODEL_NAMES, "constant_mean")
    }
    for target in targets:
        y = [_label(e, target) for e in rows]
        labelled = [i for i, v in enumerate(y) if v is not None]
        for train_idx, test_idx in folds_idx:
            tr = [i for i in train_idx if y[i] is not None]
            te = [i for i in test_idx if y[i] is not None]
            if not tr or not te:
                continue
            fold_mean = sum(y[i] for i in tr) / len(tr)
            for i in te:
                oof["constant_mean"][target][i] = fold_mean
            for name in MODEL_NAMES:
                pipe = build_pipeline(name, seed)
                pipe.fit([X[i] for i in tr], [y[i] for i in tr])
                preds = _clip(pipe.predict([X[i] for i in te]))
                for i, p in zip(te, preds):
                    oof[name][target][i] = p
        for name in (*MODEL_NAMES, "constant_mean"):
            idx = [i for i in labelled if oof[name][target][i] is not None]
            if idx:
                m = point_metrics([y[i] for i in idx], [oof[name][target][i] for i in idx])
                report["models"].setdefault(name, {})[target] = {"n": len(idx), **m}
    report["oof"] = [
        {
            "id": e.id,
            "split": "train",
            "prompt_id": e.prompt_id,
            **{f"{name}:{t}": oof[name][t][i] for name in oof for t in targets if oof[name][t][i] is not None},
        }
        for i, e in enumerate(rows)
    ]
    fitted: dict[str, dict] = {n: {} for n in MODEL_NAMES}
    for target in targets:
        y = [_label(e, target) for e in rows]
        idx = [i for i, v in enumerate(y) if v is not None]
        for name in MODEL_NAMES:
            pipe = build_pipeline(name, seed)
            pipe.fit([X[i] for i in idx], [y[i] for i in idx])
            fitted[name][target] = pipe
    fingerprint = hashlib.sha256("\n".join(sorted(f"{e.id}:{e.text_hash}" for e in rows)).encode()).hexdigest()
    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "models": fitted,
        "feature_version": FEATURE_VERSION,
        "feature_names_hash": hashlib.sha256(FEATURE_VERSION.encode()).hexdigest()[:12],
        "sklearn_version": sklearn.__version__,
        "seed": seed,
        "targets": targets,
        "train_ids": sorted(e.id for e in rows),
        "train_fingerprint": fingerprint,
        "dataset_sha256": dataset_sha256,
        "created_at": report["created_at"],
        "n_train": len(rows),
        "n_prompts": n_groups,
    }
    report["train_fingerprint"] = fingerprint
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=False)  # never overwrite a trained model
        joblib.dump(bundle, out_dir / "writing_models.joblib")
        write_report(out_dir / "training_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args(argv)
    report = train(
        read_essays(args.dataset),
        seed=args.seed,
        folds=args.folds,
        out_dir=args.out_dir,
        dataset_sha256=file_sha256(args.dataset),
    )
    for name, per_target in report["models"].items():
        o = per_target["overall"]
        print(f"{name:14s} overall CV  n={o['n']} QWK={o['qwk']} MAE={o['mae']:.3f}")
    print(f"saved to {args.out_dir}")


if __name__ == "__main__":
    main()
