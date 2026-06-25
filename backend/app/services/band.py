"""Convert a raw test score to an IELTS band (0-9).

Tables are the commonly used Academic Reading / Listening conversions for a
40-question test. For tests with fewer questions we scale the raw score to a
/40 equivalent first, so short practice tests still map to a sensible band.
"""
import math


def round_ielts(x: float) -> float:
    """Round to the nearest half-band using IELTS rules (.25 rounds UP to .5).

    Python's built-in round() uses banker's rounding, so round(6.25*2)/2 yields
    6.0 — but IELTS rounds an overall average of 6.25 up to 6.5. We round half
    up explicitly. Result is clamped to the valid 0-9 range.
    """
    return max(0.0, min(9.0, math.floor(x * 2 + 0.5) / 2))

# (min_raw_out_of_40, band) — checked from highest to lowest.
_READING = [
    (39, 9.0), (37, 8.5), (35, 8.0), (33, 7.5), (30, 7.0),
    (27, 6.5), (23, 6.0), (19, 5.5), (15, 5.0), (13, 4.5),
    (10, 4.0), (8, 3.5), (6, 3.0), (4, 2.5), (3, 2.0), (1, 1.0),
]

_LISTENING = [
    (39, 9.0), (37, 8.5), (35, 8.0), (32, 7.5), (30, 7.0),
    (26, 6.5), (23, 6.0), (18, 5.5), (16, 5.0), (13, 4.5),
    (10, 4.0), (8, 3.5), (6, 3.0), (4, 2.5), (3, 2.0), (1, 1.0),
]


def band_from_raw(score: int, total: int, test_type: str) -> float:
    if total <= 0:
        return 0.0
    raw40 = round(score / total * 40)
    table = _LISTENING if test_type == "listening" else _READING
    for threshold, band in table:
        if raw40 >= threshold:
            return band
    return 0.0
