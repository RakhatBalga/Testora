import pytest
from ml.benchmark_asr import audio_paths, benchmark
from ml.data import SpeakingSample
from ml.speech_features import Transcript


def sample(path="one.wav"):
    return SpeakingSample(sample_id="synthetic-1", speaker_id="fake-1", audio_path=path,
                          reference_text="hello world", expert_band=6, consent=True)


def test_benchmark_includes_timing_features_but_not_transcripts(tmp_path):
    audio = tmp_path / "one.wav"
    audio.write_bytes(b"synthetic-test-double")
    class Fake:
        calls = 0
        def transcribe(self, path):
            self.calls += 1
            return Transcript(text="hello", duration_seconds=2, words=[])
    engine = Fake()
    result = benchmark([sample()], audio_paths([sample()], tmp_path), engine)
    assert engine.calls == 2  # one warmup, one timed observation
    assert result["corpus_wer"] == 0.5
    assert result["real_time_factor"] >= 0
    assert result["samples"][0]["features"]["word_count"] == 1
    assert "reference_text" not in result["samples"][0]


def test_audio_root_cannot_be_escaped(tmp_path):
    root = tmp_path / "audio"
    root.mkdir()
    (tmp_path / "outside.wav").write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="inside audio-root"):
        audio_paths([sample("../outside.wav")], root)
