"""IELTS band correctness: half-up rounding + raw-score conversion."""
from app.domain.band import band_from_raw, round_ielts


def test_round_ielts_quarter_rounds_up():
    # The bug this guards: banker's rounding turned 6.25 -> 6.0 and 7.25 -> 7.0.
    assert round_ielts(6.25) == 6.5
    assert round_ielts(7.25) == 7.5


def test_round_ielts_known_cases():
    assert round_ielts(6.75) == 7.0
    assert round_ielts(5.75) == 6.0
    assert round_ielts(6.125) == 6.0
    assert round_ielts(6.5) == 6.5


def test_round_ielts_clamped():
    assert round_ielts(-1) == 0.0
    assert round_ielts(12) == 9.0


def test_band_from_raw_full_length_reading():
    assert band_from_raw(40, 40, "reading") == 9.0
    assert band_from_raw(30, 40, "reading") == 7.0
    assert band_from_raw(0, 40, "reading") == 0.0


def test_band_from_raw_zero_total_is_zero():
    assert band_from_raw(0, 0, "reading") == 0.0


def test_band_from_raw_listening_table_differs():
    # Listening 32/40 -> 7.5, reading 32/40 -> 7.0 (different cutoffs).
    assert band_from_raw(32, 40, "listening") == 7.5
    assert band_from_raw(32, 40, "reading") == 7.0
