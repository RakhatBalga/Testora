import pytest

pytest.importorskip("sklearn")
from ml.speech_features import FEATURE_NAMES
from ml.train_speaking import train_compare


def synthetic_rows():
    return [
        dict(
            sample_id=f"fake-{i}-{j}",
            speaker_id=f"fake-{i}",
            expert_band=4 + i * 0.5,
            llm_band=4 + i * 0.5,
            features={name: (None if name == "mean_asr_confidence" else float(i + j)) for name in FEATURE_NAMES},
        )
        for i in range(8)
        for j in range(2)
    ]


def test_training_has_no_speaker_leakage_and_is_repeatable():
    first, second = train_compare(synthetic_rows()), train_compare(synthetic_rows())
    assert set(first["train_speakers"]).isdisjoint(first["test_speakers"])
    assert first == second
    assert first["models"]["llm_transcript"]["mae"] == 0
    for name in ("mean_baseline", "linear_regression", "gradient_boosting"):
        assert first["models"][name]["mae"] >= 0


def test_training_rejects_duplicate_or_insufficient_speakers():
    with pytest.raises(ValueError, match="Duplicate"):
        train_compare(synthetic_rows() + synthetic_rows()[:1])
    with pytest.raises(ValueError, match="four"):
        train_compare(synthetic_rows()[:4])


def test_band_agreement_uses_unrounded_predictions_and_inclusive_boundary():
    from ml.train_speaking import score_summary

    metrics = score_summary([5, 6, 7], [5.5, 7, 8.1])
    assert metrics["within_half_band"] == pytest.approx(1 / 3)
    assert metrics["within_one_band"] == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        score_summary([5], [float("nan")])


def test_signed_error_distinguishes_overgrading_from_undergrading():
    from ml.train_speaking import score_summary

    over = score_summary([5, 6], [6, 7])
    under = score_summary([5, 6], [4, 5])
    assert over["mean_signed_error"] == 1
    assert under["mean_signed_error"] == -1
    assert over["rmse"] == under["rmse"] == 1


def test_missingness_report_keeps_train_and_test_separate():
    report = train_compare(synthetic_rows())
    for split, count_key in [("train", "train_count"), ("holdout", "test_count")]:
        missing = report["feature_missingness"][split]
        assert missing["mean_asr_confidence"]["missing"] == report[count_key]
        assert missing["word_count"]["missing"] == 0
        assert missing["word_count"]["total"] == report[count_key]


def test_shuffling_manifest_does_not_change_speaking_results():
    assert train_compare(synthetic_rows()) == train_compare(list(reversed(synthetic_rows())))


def test_split_manifest_accounts_for_every_sample_once():
    report = train_compare(synthetic_rows())
    train, held = map(set, [report["split_samples"]["train"], report["split_samples"]["holdout"]])
    assert train.isdisjoint(held)
    assert train | held == {r["sample_id"] for r in synthetic_rows()}
    assert sum(report["band_distribution"]["train"].values()) == len(train)
    assert sum(report["band_distribution"]["holdout"].values()) == len(held)


def test_incomplete_llm_coverage_never_produces_subset_metrics():
    rows = synthetic_rows()
    complete = train_compare(rows)
    held_id = complete["split_samples"]["holdout"][0]
    next(r for r in rows if r["sample_id"] == held_id)["llm_band"] = None
    result = train_compare(rows)["models"]["llm_transcript"]
    assert result["status"] == "missing_held_out_scores"
    assert "mae" not in result
    assert result["coverage"]["available"] == result["coverage"]["required"] - 1
    assert len(complete["models"]["llm_transcript"]["predictions"]) == complete["test_count"]


def test_cli_passes_requested_holdout_fraction(tmp_path, monkeypatch):
    import json
    import ml.train_speaking as module

    source = tmp_path / "benchmark.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "asr-comparison.v1",
                "runs": [{"config": {"model": "tiny.en"}, "feature_version": module.FEATURE_VERSION, "samples": []}],
            }
        )
    )
    seen = {}

    def capture(rows, **kwargs):
        seen.update(kwargs)
        return {}

    monkeypatch.setattr(module, "train_compare", capture)
    module.main([str(source), "--model", "tiny.en", "--test-size", "0.4", "--output", str(tmp_path / "report.json")])
    assert seen["test_size"] == 0.4


def test_model_artifacts_require_a_new_run_directory(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    model = directory / "linear_regression.joblib"
    model.write_bytes(b"previous-model")
    with pytest.raises(FileExistsError):
        train_compare(synthetic_rows(), artifacts=directory)
    assert model.read_bytes() == b"previous-model"
    assert list(directory.iterdir()) == [model]
