"""Agreement statistics for E1: point metrics, bootstrap CIs, stability, compression.

Pure Python on top of the verified ml.metrics (QWK etc.); no numpy needed.
Convention: `actual` are human half bands; `predicted` may be continuous (ML
regressors). QWK and exact agreement use predictions snapped to half bands, every
other metric uses the raw prediction clipped to [0, 9].
"""

import math
import random
from collections import Counter

from ml.metrics import half_band, mae, qwk

TOLERANCE_EPS = 1e-9
POINT_METRICS = ("qwk", "mae", "rmse", "bias", "exact", "within_0_5", "within_1_0", "pearson", "spearman")
_CI_FAST = ("qwk", "mae")
FLAG_REQUIRED_TRUE = ("overview_present", "key_comparisons_present", "all_parts_addressed", "position_clear")
FLAG_FAILURE_TRUE = ("off_topic", "data_accuracy_issue", "fabricated_data")


def _clip(values):
    return [min(9.0, max(0.0, float(v))) for v in values]


def mean(values):
    return sum(values) / len(values)


def sd(values):
    """Sample SD (n-1); 0.0 for a single value."""
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def pearson(x, y):
    if len(x) < 2:
        return None
    mx, my = mean(x), mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None  # a constant has no correlation; do not report 0 or 1
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)


def _ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x, y):
    return pearson(_ranks(x), _ranks(y))


def point_metrics(actual, predicted, names=POINT_METRICS) -> dict:
    """Metrics for aligned lists; None where undefined (never a fake 0)."""
    p = _clip(predicted)
    snapped = [half_band(v) for v in p]
    n = len(actual)
    out = {}
    if "qwk" in names:
        out["qwk"] = qwk(list(actual), snapped)
    if "mae" in names:
        out["mae"] = mae(list(actual), p)
    if "rmse" in names:
        out["rmse"] = math.sqrt(sum((a - b) ** 2 for a, b in zip(actual, p)) / n)
    if "bias" in names:
        out["bias"] = sum(b - a for a, b in zip(actual, p)) / n
    if "exact" in names:
        out["exact"] = sum(a == b for a, b in zip(actual, snapped)) / n
    if "within_0_5" in names:
        out["within_0_5"] = sum(abs(a - b) <= 0.5 + TOLERANCE_EPS for a, b in zip(actual, p)) / n
    if "within_1_0" in names:
        out["within_1_0"] = sum(abs(a - b) <= 1.0 + TOLERANCE_EPS for a, b in zip(actual, p)) / n
    if "pearson" in names:
        out["pearson"] = pearson(list(actual), p)
    if "spearman" in names:
        out["spearman"] = spearman(list(actual), p)
    return out


def spread_stats(actual, predicted) -> dict:
    """Score-compression diagnostics (the audit found a flat 7.0 problem)."""
    p = _clip(predicted)
    snapped = [half_band(v) for v in p]
    mode_value, mode_count = Counter(snapped).most_common(1)[0]
    sd_pred, sd_label = sd(p), sd(list(actual))
    return {
        "n_unique_predictions": len(set(snapped)),
        "mean_prediction": mean(p),
        "mean_label": mean(list(actual)),
        "sd_prediction": sd_pred,
        "sd_label": sd_label,
        "sd_ratio": (sd_pred / sd_label) if sd_label > 0 else None,
        "mode_value": mode_value,
        "mode_share": mode_count / len(p),
    }


def confusion_matrix(actual, predicted) -> dict:
    snapped = [half_band(v) for v in _clip(predicted)]
    labels = sorted(set(actual) | set(snapped))
    index = {b: i for i, b in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for a, b in zip(actual, snapped):
        matrix[index[a]][index[b]] += 1
    return {"labels": labels, "rows_are": "human", "cols_are": "system", "matrix": matrix}


def _percentile(sorted_values, q):
    if not sorted_values:
        return None
    pos = q * (len(sorted_values) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def _resample(n, clusters, rng):
    if clusters is None:
        return [rng.randrange(n) for _ in range(n)]
    groups: dict = {}
    for i, c in enumerate(clusters):
        groups.setdefault(c, []).append(i)
    keys = list(groups)
    idx = []
    for _ in keys:
        idx.extend(groups[keys[rng.randrange(len(keys))]])
    return idx


def bootstrap_ci(actual, predicted, *, names=POINT_METRICS, n_boot=2000, seed=0, clusters=None, level=0.95) -> dict:
    """Percentile bootstrap CI per metric. `clusters` (e.g. prompt ids) enables a
    cluster bootstrap that resamples whole groups. Resamples where a metric is
    undefined are skipped and counted in `n_valid`."""
    rng = random.Random(seed)
    draws = {name: [] for name in names}
    a, p = list(actual), list(predicted)
    for _ in range(n_boot):
        idx = _resample(len(a), clusters, rng)
        pm = point_metrics([a[i] for i in idx], [p[i] for i in idx], names)
        for name in names:
            if pm[name] is not None:
                draws[name].append(pm[name])
    alpha = (1 - level) / 2
    out = {}
    for name, values in draws.items():
        values.sort()
        out[name] = {"lo": _percentile(values, alpha), "hi": _percentile(values, 1 - alpha), "n_valid": len(values)}
    return out


def paired_bootstrap_diff(
    actual, pred_a, pred_b, *, names=_CI_FAST, n_boot=2000, seed=0, clusters=None, level=0.95
) -> dict:
    """Metric(A) - metric(B) on the SAME resampled essays, with a two-sided
    bootstrap p-value (share of resamples on either side of zero)."""
    rng = random.Random(seed)
    a, pa, pb = list(actual), list(pred_a), list(pred_b)
    draws = {name: [] for name in names}
    for _ in range(n_boot):
        idx = _resample(len(a), clusters, rng)
        ra = point_metrics([a[i] for i in idx], [pa[i] for i in idx], names)
        rb = point_metrics([a[i] for i in idx], [pb[i] for i in idx], names)
        for name in names:
            if ra[name] is not None and rb[name] is not None:
                draws[name].append(ra[name] - rb[name])
    base_a, base_b = point_metrics(a, pa, names), point_metrics(a, pb, names)
    alpha = (1 - level) / 2
    out = {}
    for name, values in draws.items():
        values.sort()
        le = sum(v <= 0 for v in values) / len(values) if values else None
        ge = sum(v >= 0 for v in values) / len(values) if values else None
        out[name] = {
            "diff": (None if base_a[name] is None or base_b[name] is None else base_a[name] - base_b[name]),
            "lo": _percentile(values, alpha),
            "hi": _percentile(values, 1 - alpha),
            "p_two_sided": None if le is None else min(1.0, 2 * min(le, ge)),
            "n_valid": len(values),
        }
    return out


def icc_2_1(matrix) -> float | None:
    """ICC(2,1): two-way random, absolute agreement, single rating.
    `matrix` is n essays x k runs, complete. None if undefined."""
    n = len(matrix)
    k = len(matrix[0]) if n else 0
    if n < 2 or k < 2:
        return None
    grand = sum(sum(r) for r in matrix) / (n * k)
    row_means = [sum(r) / k for r in matrix]
    col_means = [sum(matrix[i][j] for i in range(n)) / n for j in range(k)]
    ssr = k * sum((m - grand) ** 2 for m in row_means)
    ssc = n * sum((m - grand) ** 2 for m in col_means)
    sst = sum((v - grand) ** 2 for r in matrix for v in r)
    sse = sst - ssr - ssc
    msr, msc = ssr / (n - 1), ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    denom = msr + (k - 1) * mse + k * (msc - mse) / n
    if denom == 0:
        return None
    return (msr - mse) / denom


def stability(runs_by_essay: dict[str, list[float]]) -> dict | None:
    """Run-to-run stability. `runs_by_essay`: essay id -> band per run (equal
    length for essays with a full set of runs; incomplete essays are excluded and
    counted)."""
    if not runs_by_essay:
        return None
    k = max(len(v) for v in runs_by_essay.values())
    full = {e: v for e, v in runs_by_essay.items() if len(v) == k}
    if k < 2 or len(full) < 2:
        return {
            "n_runs": k,
            "n_essays": len(full),
            "n_incomplete": len(runs_by_essay) - len(full),
            "note": "needs >= 2 runs on >= 2 essays",
        }
    matrix = [v for v in full.values()]
    pair_qwk = []
    for i in range(k):
        for j in range(i + 1, k):
            q = qwk([half_band(r[i]) for r in matrix], [half_band(r[j]) for r in matrix])
            if q is not None:
                pair_qwk.append(q)
    sds = [sd(r) for r in matrix]
    return {
        "n_runs": k,
        "n_essays": len(full),
        "n_incomplete": len(runs_by_essay) - len(full),
        "mean_within_essay_sd": mean(sds),
        "max_within_essay_sd": max(sds),
        "pct_essays_any_flip": sum(len(set(r)) > 1 for r in matrix) / len(matrix),
        "icc_2_1": icc_2_1(matrix),
        "mean_pairwise_qwk": mean(pair_qwk) if pair_qwk else None,
    }


def cap_hit(flags: dict | None) -> bool | None:
    """True if an examiner cap flag fired; None when flags are unavailable."""
    if not flags:
        return None
    return any(flags.get(f) is False for f in FLAG_REQUIRED_TRUE) or any(
        flags.get(f) is True for f in FLAG_FAILURE_TRUE
    )
