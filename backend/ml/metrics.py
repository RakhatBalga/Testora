"""Small dependency-free metrics with explicit undefined-result handling."""

import math
import re
from collections import Counter


def words(text: str) -> list[str]:
    """English WER normalization v1: lowercase, punctuation removed, apostrophes kept."""
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)*", text.lower().replace("’", "'"))


def word_errors(reference: str, hypothesis: str) -> tuple[int, int]:
    ref, hyp = words(reference), words(hypothesis)
    previous = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        current = [i]
        for j, b in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1], len(ref)


def corpus_wer(references: list[str], hypotheses: list[str]) -> float:
    if not references or len(references) != len(hypotheses):
        raise ValueError("Expected nonempty aligned transcripts")
    pairs = [word_errors(r, h) for r, h in zip(references, hypotheses)]
    count = sum(n for _, n in pairs)
    if count == 0:
        raise ValueError("WER is undefined with no reference words")
    return sum(e for e, _ in pairs) / count


def _pairs(actual, predicted):
    if not actual or len(actual) != len(predicted):
        raise ValueError("Expected nonempty aligned observations")
    if not all(math.isfinite(v) for v in [*actual, *predicted]):
        raise ValueError("Observations must be finite")
    return list(zip(actual, predicted))


def mae(actual: list[float], predicted: list[float]) -> float:
    pairs = _pairs(actual, predicted)
    return sum(abs(a - b) for a, b in pairs) / len(pairs)


def half_band(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("Band must be finite")
    return math.floor(min(9, max(0, value)) * 2 + 0.5) / 2


def qwk(actual: list[float], predicted: list[float]) -> float | None:
    """Quadratic weighted kappa on the fixed 0..9 half-band ordinal scale.

    Inputs must already be half bands. None means both raters use one identical
    category, so chance disagreement and the kappa denominator are zero.
    """
    pairs = _pairs(actual, predicted)
    if any(not 0 <= x <= 9 or x * 2 != round(x * 2) for pair in pairs for x in pair):
        raise ValueError("QWK requires half bands in [0, 9]")
    a, b = Counter(actual), Counter(predicted)
    observed = sum((x - y) ** 2 for x, y in pairs)
    expected = sum(nx * ny * (x - y) ** 2 for x, nx in a.items() for y, ny in b.items()) / len(pairs)
    return None if expected == 0 else 1 - observed / expected


def auc(labels: list[int], probabilities: list[float]) -> float | None:
    """ROC AUC by averaged ranks; ties receive half credit."""
    pairs = _pairs(labels, probabilities)
    if any(y not in (0, 1) or not 0 <= p <= 1 for y, p in pairs):
        raise ValueError("AUC requires binary labels and probabilities in [0, 1]")
    positive = sum(labels)
    negative = len(labels) - positive
    if not positive or not negative:
        return None
    ordered = sorted(pairs, key=lambda pair: pair[1])
    rank_sum = 0.0
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        rank_sum += sum(y for y, _ in ordered[i:j]) * (i + 1 + j) / 2
        i = j
    return (rank_sum - positive * (positive + 1) / 2) / (positive * negative)


def brier(labels: list[int], probabilities: list[float]) -> float:
    pairs = _pairs(labels, probabilities)
    if any(y not in (0, 1) or not 0 <= p <= 1 for y, p in pairs):
        raise ValueError("Expected binary labels and probabilities in [0, 1]")
    return sum((y - p) ** 2 for y, p in pairs) / len(pairs)


def log_loss(labels: list[int], probabilities: list[float]) -> float:
    brier(labels, probabilities)  # Shared validation, including finite values.
    epsilon = 1e-15
    clipped = [min(1 - epsilon, max(epsilon, p)) for p in probabilities]
    return -sum(y * math.log(p) + (1 - y) * math.log1p(-p) for y, p in zip(labels, clipped)) / len(labels)


def reliability_bins(labels: list[int], probabilities: list[float], bins: int = 10) -> list[dict]:
    brier(labels, probabilities)
    if isinstance(bins, bool) or not isinstance(bins, int) or bins < 1:
        raise ValueError("bins must be a positive integer")
    groups = [[] for _ in range(bins)]
    for y, p in zip(labels, probabilities):
        groups[min(bins - 1, int(p * bins))].append((y, p))
    return [
        {
            "lower": i / bins,
            "upper": (i + 1) / bins,
            "count": len(group),
            "mean_probability": sum(p for _, p in group) / len(group) if group else None,
            "observed_correct": sum(y for y, _ in group) / len(group) if group else None,
        }
        for i, group in enumerate(groups)
    ]


def band_agreement(actual: list[float], predicted: list[float], tolerance: float = 0.5) -> float:
    pairs = _pairs(actual, predicted)
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Tolerance must be finite and nonnegative")
    if any(not 0 <= v <= 9 for pair in pairs for v in pair):
        raise ValueError("Expected bands in [0, 9]")
    return sum(abs(a - p) <= tolerance for a, p in pairs) / len(pairs)
