import pytest
from ml.speech_features import Transcript, extract_features


def test_fluency_proxies_have_known_values():
    transcript = Transcript(
        text="Um I I agree",
        duration_seconds=4,
        words=[
            dict(text="Um", start=0, end=0.5, probability=0.8),
            dict(text="I", start=1, end=1.5, probability=0.9),
            dict(text="I", start=1.5, end=2, probability=0.9),
            dict(text="agree", start=3, end=3.5, probability=1),
        ],
    )
    features = extract_features(transcript)
    assert features["words_per_minute"] == 60
    assert features["articulation_words_per_minute"] == 120
    assert features["pause_count"] == 2
    assert features["interword_pause_ratio"] == 0.375
    assert features["filler_ratio"] == 0.25
    assert features["immediate_repeat_ratio"] == pytest.approx(1 / 3)
    assert features["mean_asr_confidence"] == pytest.approx(0.9)


def test_missing_timing_is_not_reported_as_perfect_fluency():
    result = extract_features(Transcript(text="hello", duration_seconds=2, words=[]))
    assert result["pause_count"] is None
    assert result["mean_asr_confidence"] is None


@pytest.mark.parametrize("word", [dict(start=1, end=0), dict(start=0, end=4)])
def test_invalid_timestamps_fail(word):
    with pytest.raises(ValueError):
        Transcript(text="hello", duration_seconds=2, words=[dict(text="hello", **word)])
