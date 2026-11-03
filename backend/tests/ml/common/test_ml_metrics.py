import pytest
from ml.metrics import auc, corpus_wer, half_band, mae, qwk, word_errors


def test_wer_counts_edits_and_weights_by_reference_length():
    assert word_errors("I like tea", "I really like coffee") == (2, 3)
    assert corpus_wer(["hello", "one two three"], ["", "one two three"]) == 0.25
    assert corpus_wer(["Hello, WORLD!"], ["hello world"]) == 0
    assert corpus_wer(["one"], ["one two three"]) == 2
    with pytest.raises(ValueError):
        corpus_wer([""], ["hello"])


def test_band_metrics_and_undefined_kappa():
    assert mae([5, 7], [6, 7]) == 0.5
    assert qwk([5, 7], [5, 7]) == 1
    assert qwk([5, 7], [7, 5]) == -1
    assert qwk([6, 6], [6, 6]) is None
    assert half_band(6.25) == 6.5
    assert half_band(10) == 9
    with pytest.raises(ValueError):
        qwk([6], [6.1])


def test_auc_handles_ties_order_and_missing_classes():
    assert auc([0, 1, 0, 1], [0.1, 0.8, 0.2, 0.9]) == 1
    assert auc([0, 1], [0.5, 0.5]) == 0.5
    assert auc([0, 1], [0.9, 0.1]) == 0
    assert auc([1, 1], [0.5, 0.9]) is None
    with pytest.raises(ValueError):
        auc([0, 1], [0.1, float("nan")])
    with pytest.raises(ValueError):
        mae([], [])


def test_brier_validates_probabilities_and_scores_calibration():
    from ml.metrics import brier

    assert brier([0, 1], [0, 1]) == 0
    assert brier([0, 1], [0.5, 0.5]) == 0.25
    with pytest.raises(ValueError):
        brier([1], [1.1])


def test_log_loss_penalizes_confident_errors_and_handles_endpoints():
    from ml.metrics import log_loss

    assert log_loss([0, 1], [0, 1]) < 1e-10
    assert log_loss([0, 1], [1, 0]) > log_loss([0, 1], [0.5, 0.5])
    with pytest.raises(ValueError):
        log_loss([0], [float("nan")])


def test_reliability_bins_include_one_and_preserve_empty_groups():
    from ml.metrics import reliability_bins

    bins = reliability_bins([0, 1, 1], [0, 0.5, 1], bins=4)
    assert [b["count"] for b in bins] == [1, 0, 1, 1]
    assert bins[1]["observed_correct"] is None
    assert bins[-1]["mean_probability"] == 1
    with pytest.raises(ValueError):
        reliability_bins([1], [0.5], bins=0)
