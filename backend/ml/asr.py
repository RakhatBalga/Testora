"""Optional faster-whisper adapter. No model download or import on API startup."""
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from ml.speech_features import TimedWord, Transcript


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> Transcript: ...


@dataclass(frozen=True)
class WhisperConfig:
    model: str = "tiny.en"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    allow_download: bool = False

    def __post_init__(self):
        if self.beam_size < 1:
            raise ValueError("beam_size must be positive")


class FasterWhisperTranscriber:
    def __init__(self, config: WhisperConfig, *, model_factory=None):
        if model_factory is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError("Install requirements-asr.txt to run Whisper") from exc
            model_factory = WhisperModel
        self.config = config
        start = perf_counter()
        self.model = model_factory(
            config.model, device=config.device, compute_type=config.compute_type,
            local_files_only=not config.allow_download,
        )
        self.load_seconds = perf_counter() - start

    def transcribe(self, audio_path: Path) -> Transcript:
        if not audio_path.is_file():
            raise ValueError("Audio file does not exist")
        segments, info = self.model.transcribe(
            str(audio_path), language="en", beam_size=self.config.beam_size,
            word_timestamps=True, vad_filter=False, condition_on_previous_text=False,
        )
        # faster-whisper returns a lazy iterator: consuming it is part of inference.
        text, timed = [], []
        for segment in segments:
            text.append(segment.text.strip())
            for word in segment.words or []:
                timed.append(TimedWord(text=word.word, start=word.start, end=word.end,
                                       probability=word.probability))
        return Transcript(text=" ".join(text), duration_seconds=info.duration, words=timed)
