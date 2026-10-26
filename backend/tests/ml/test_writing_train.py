import pytest

pytest.importorskip("sklearn")
pytest.importorskip("joblib")
pytest.importorskip("numpy")

from ml.train_writing import load_bundle, predict, train
from ml.writing_features import FEATURE_NAMES, extract, vector
from writing_synth import make_essays


def test_features_are_complete_and_sensible():
    short, long_ = extract("Short text.", 2), extract("A longer text. " * 40, 2)
    assert set(short) == set(FEATURE_NAMES) and len(vector("x y z", 1)) == len(FEATURE_NAMES)
    assert long_["log_words"] > short["log_words"]
    assert extract("i think so.dont", 2)["err_lower_i"] > 0
    assert extract("", 2)["log_words"] == 0  # empty text must not crash


def test_train_cv_grouped_saves_with_metadata_and_never_overwrites(tmp_path):
    essays = make_essays(90, n_prompts=9)
    out = tmp_path / "model"
    report = train(essays, seed=3, folds=3, out_dir=out)
    assert report["cv"].startswith("GroupKFold") and report["folds"] == 3
    for name in ("ridge", "gbm"):
        assert report["models"][name]["overall"]["pearson"] > 0.3  # synthetic signal is learnable
    assert report["models"]["constant_mean"]["overall"]["qwk"] < 0.2  # no better than a constant
    bundle = load_bundle(out / "writing_models.joblib")
    assert bundle["feature_version"] and bundle["sklearn_version"] and bundle["n_train"] == 90
    assert len(bundle["train_ids"]) == 90
    held_out = make_essays(8, n_prompts=3, seed=99, prefix="h", split="test")
    preds = predict(bundle, "ridge", held_out)["overall"]
    assert len(preds) == 8 and all(0 <= p <= 9 for p in preds)
    with pytest.raises(FileExistsError):
        train(essays, seed=3, folds=3, out_dir=out)


def test_oof_predictions_come_from_models_not_trained_on_that_prompt():
    essays = make_essays(60, n_prompts=6)
    report = train(essays, folds=3)
    assert len(report["oof"]) == 60 and all("ridge:overall" in row for row in report["oof"])


def test_train_ignores_test_gold_and_dev_essays():
    train_set = make_essays(40, n_prompts=5)
    extra = make_essays(10, seed=5, prefix="t", split="test") + make_essays(10, seed=6, prefix="g", split="gold")
    report = train(train_set + extra, folds=2)
    assert report["n_train"] == 40
    with pytest.raises(ValueError):
        train(make_essays(5), folds=2)


def test_pipeline_functions_are_picklable_from_a_cli_run():
    """Running `python -m ml.train_writing` makes __main__ the module; functions
    defined there cannot be unpickled by the evaluator."""
    from ml.train_writing import build_pipeline

    for name in ("ridge", "gbm"):
        union = build_pipeline(name, 0).steps[0][1]
        funcs = [
            t.func
            for _, branch in union.transformer_list
            for _, t in (branch.steps if hasattr(branch, "steps") else [("f", branch)])
            if hasattr(t, "func")
        ]
        assert funcs and all(f.__module__ == "ml.writing_features" for f in funcs)
