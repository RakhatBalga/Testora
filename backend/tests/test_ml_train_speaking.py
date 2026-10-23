import pytest
pytest.importorskip("sklearn")
from ml.speech_features import FEATURE_NAMES
from ml.train_speaking import train_compare


def synthetic_rows():
    return [dict(sample_id=f"fake-{i}-{j}", speaker_id=f"fake-{i}", expert_band=4 + i * 0.5,
                 llm_band=4 + i * 0.5,
                 features={name: (None if name == "mean_asr_confidence" else float(i + j)) for name in FEATURE_NAMES})
            for i in range(8) for j in range(2)]


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
    assert metrics['within_half_band'] == pytest.approx(1 / 3)
    assert metrics['within_one_band'] == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        score_summary([5], [float('nan')])


def test_signed_error_distinguishes_overgrading_from_undergrading():
    from ml.train_speaking import score_summary
    over = score_summary([5, 6], [6, 7])
    under = score_summary([5, 6], [4, 5])
    assert over['mean_signed_error'] == 1
    assert under['mean_signed_error'] == -1
    assert over['rmse'] == under['rmse'] == 1
