import json
import pytest
from ml.data import ResponseRecord, SpeakingSample, read_jsonl


def test_research_data_requires_consent_and_valid_band():
    row = dict(sample_id="s1", speaker_id="p1", audio_path="one.wav",
               reference_text="A synthetic test.", expert_band=6.5, consent=True)
    assert SpeakingSample(**row).expert_band == 6.5
    for change in ({"consent": False}, {"expert_band": 6.2}, {"expert_band": float("nan")}):
        with pytest.raises(ValueError):
            SpeakingSample(**(row | change))


def test_response_requires_timezone_and_boolean():
    row = dict(response_id="r", learner_id="u", item_id="q", content_version="v1",
               skill="reading", question_type="choice", correct=True, answered_at="2026-10-14T10:00:00Z")
    assert ResponseRecord(**row).item_key != ResponseRecord(**(row | {"content_version": "v2"})).item_key
    for change in ({"correct": "false"}, {"answered_at": "2026-10-14T10:00:00"}):
        with pytest.raises(ValueError):
            ResponseRecord(**(row | change))


def test_duplicate_samples_are_rejected_without_echoing_text(tmp_path):
    row = dict(sample_id="s1", speaker_id="p1", audio_path="one.wav",
               reference_text="private text", expert_band=6, consent=True)
    path = tmp_path / "samples.jsonl"
    path.write_text((json.dumps(row) + "\n") * 2)
    with pytest.raises(ValueError, match="line 2") as error:
        read_jsonl(path, SpeakingSample)
    assert "private text" not in str(error.value)
