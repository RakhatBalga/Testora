from types import SimpleNamespace as NS
from ml.asr import FasterWhisperTranscriber, WhisperConfig


def test_whisper_is_local_by_default_and_consumes_lazy_segments(tmp_path):
    captured = {}

    class FakeModel:
        def __init__(self, model, **kwargs):
            captured.update(kwargs)

        def transcribe(self, path, **kwargs):
            captured.update(kwargs)

            def segments():
                captured["consumed"] = True
                yield NS(text=" Hello", words=[NS(word="Hello", start=0, end=1, probability=0.9)])

            return segments(), NS(duration=2)

    audio = tmp_path / "synthetic.wav"
    audio.write_bytes(b"test-double-only")
    engine = FasterWhisperTranscriber(WhisperConfig(), model_factory=FakeModel)
    result = engine.transcribe(audio)
    assert captured["local_files_only"] is True
    assert captured["consumed"] is True
    assert captured["vad_filter"] is False
    assert captured["word_timestamps"] is True
    assert result.text == "Hello"
    assert result.words[0].probability == 0.9
