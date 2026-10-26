
import pytest

from ml import writing_stats as ws
from ml.metrics import qwk

LABELS = [5.5, 6.0, 6.0, 6.5, 6.5, 7.0, 7.0, 7.5] * 5


def test_constant_predictor_has_zero_qwk_but_decent_mae():
    """The audit finding: a flat 7.0 looks fine on MAE and within-0.5 but is worthless."""
    pred = [7.0] * len(LABELS)
    m = ws.point_metrics(LABELS, pred)
    assert m["qwk"] == pytest.approx(0.0, abs=1e-12)
    assert m["mae"] < 0.7
    assert m["within_0_5"] >= 0.6
    assert m["pearson"] is None and m["spearman"] is None  # undefined, not a fake number
    s = ws.spread_stats(LABELS, pred)
    assert s["mode_share"] == 1.0 and s["sd_prediction"] == 0 and s["sd_ratio"] == 0


def test_perfect_and_noisy_predictions():
    assert ws.point_metrics(LABELS, LABELS)["qwk"] == pytest.approx(1.0)
    shifted = [v + 0.5 for v in LABELS]
    m = ws.point_metrics(LABELS, shifted)
    assert m["bias"] == pytest.approx(0.5) and m["mae"] == pytest.approx(0.5)
    assert m["exact"] == 0 and m["within_0_5"] == 1.0 and m["pearson"] == pytest.approx(1.0)


def test_qwk_matches_sklearn_on_half_band_bins():
    sk = pytest.importorskip("sklearn.metrics")
    pred = [min(9, max(0, v + d)) for v, d in zip(LABELS, [0, 0.5, -0.5, 1.0, 0, 0, -1.0, 0.5] * 5)]
    ours = ws.point_metrics(LABELS, pred)["qwk"]
    theirs = sk.cohen_kappa_score([int(v * 2) for v in LABELS], [int(v * 2) for v in pred], weights="quadratic")
    assert ours == pytest.approx(theirs)
    assert ours == pytest.approx(qwk(LABELS, pred))


def test_spearman_handles_ties():
    assert ws.spearman([1, 2, 2, 3], [10, 20, 20, 30]) == pytest.approx(1.0)
    assert ws.spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)


def test_confusion_matrix_counts():
    c = ws.confusion_matrix([6.0, 6.0, 7.0], [6.0, 7.0, 7.0])
    assert c["labels"] == [6.0, 7.0] and c["matrix"] == [[1, 1], [0, 1]]


def test_bootstrap_ci_is_reproducible_and_brackets_point():
    pred = [min(9, v + (0.5 if i % 3 == 0 else 0)) for i, v in enumerate(LABELS)]
    a = ws.bootstrap_ci(LABELS, pred, n_boot=300, seed=3)
    b = ws.bootstrap_ci(LABELS, pred, n_boot=300, seed=3)
    assert a == b
    point = ws.point_metrics(LABELS, pred)
    assert a["mae"]["lo"] <= point["mae"] <= a["mae"]["hi"]
    assert a["qwk"]["lo"] <= point["qwk"] <= a["qwk"]["hi"]


def test_cluster_bootstrap_runs():
    clusters = [i % 8 for i in range(len(LABELS))]
    out = ws.bootstrap_ci(LABELS, LABELS, names=("mae",), n_boot=50, clusters=clusters)
    assert out["mae"]["lo"] == 0 == out["mae"]["hi"]


def test_paired_bootstrap_separates_good_from_flat():
    good = [v + (0.5 if i % 4 == 0 else 0) for i, v in enumerate(LABELS)]
    flat = [7.0] * len(LABELS)
    d = ws.paired_bootstrap_diff(LABELS, good, flat, n_boot=300, seed=1)
    assert d["qwk"]["diff"] > 0.5 and d["qwk"]["lo"] > 0 and d["qwk"]["p_two_sided"] < 0.05
    same = ws.paired_bootstrap_diff(LABELS, good, good, n_boot=100, seed=1)
    assert same["qwk"]["diff"] == 0 and same["qwk"]["lo"] == 0 == same["qwk"]["hi"]


def test_icc_perfect_and_noisy():
    perfect = [[v, v, v] for v in LABELS]
    assert ws.icc_2_1(perfect) == pytest.approx(1.0)
    noisy = [[v, v + (0.5 if i % 2 else -0.5), v] for i, v in enumerate(LABELS)]
    assert 0.5 < ws.icc_2_1(noisy) < 1.0
    assert ws.icc_2_1([[1.0, 1.0], [1.0, 1.0]]) is None


def test_stability_counts_flips_and_incomplete():
    runs = {"a": [6.0, 6.0, 6.0], "b": [6.0, 6.5, 6.0], "c": [7.0, 7.0, 7.0], "d": [5.0, 6.0, 5.5], "e": [6.0]}
    s = ws.stability(runs)
    assert s["n_runs"] == 3 and s["n_essays"] == 4 and s["n_incomplete"] == 1
    assert s["pct_essays_any_flip"] == 0.5
    assert s["mean_within_essay_sd"] > 0


def test_cap_hit_requires_flags():
    assert ws.cap_hit(None) is None
    assert ws.cap_hit({"off_topic": False, "position_clear": True}) is False
    assert ws.cap_hit({"off_topic": True}) is True
    assert ws.cap_hit({"overview_present": False}) is True
