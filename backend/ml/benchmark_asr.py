"""Run with: python -m ml.benchmark_asr manifest.jsonl --audio-root DIR --output FILE."""
import argparse
import hashlib
import importlib.metadata
import platform
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from ml.asr import FasterWhisperTranscriber, WhisperConfig
from ml.data import SpeakingSample, read_jsonl, write_report
from ml.metrics import corpus_wer, word_errors
from ml.speech_features import FEATURE_VERSION, extract_features


def audio_paths(samples: list[SpeakingSample], root: Path) -> list[Path]:
    root = root.resolve()
    paths = []
    for sample in samples:
        path = (root / sample.audio_path).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Sample {sample.sample_id}: audio must exist inside audio-root")
        paths.append(path)
    return paths


def benchmark(samples, paths, engine, *, warmup=True) -> dict:
    if not samples or len(samples) != len(paths):
        raise ValueError("Expected nonempty aligned samples and paths")
    if warmup:
        engine.transcribe(paths[0])
    references, hypotheses, rows = [], [], []
    for sample, path in zip(samples, paths):
        start = perf_counter()
        transcript = engine.transcribe(path)
        elapsed = perf_counter() - start
        references.append(sample.reference_text)
        hypotheses.append(transcript.text)
        edits, reference_words = word_errors(sample.reference_text, transcript.text)
        rows.append({
            "sample_id": sample.sample_id, "speaker_id": sample.speaker_id,
            "expert_band": sample.expert_band, "llm_band": sample.llm_band,
            "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "duration_seconds": transcript.duration_seconds, "inference_seconds": elapsed,
            "word_errors": edits, "reference_words": reference_words,
            "features": extract_features(transcript),
        })
    duration = sum(row["duration_seconds"] for row in rows)
    elapsed = sum(row["inference_seconds"] for row in rows)
    return {
        "schema_version": "asr-benchmark.v1", "feature_version": FEATURE_VERSION,
        "sample_count": len(rows), "warmup_recordings": int(warmup),
        "corpus_wer": corpus_wer(references, hypotheses),
        "inference_seconds": elapsed, "audio_seconds": duration,
        "real_time_factor": elapsed / duration, "samples": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", nargs="+", default=["tiny.en", "base.en"])
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()
    samples = read_jsonl(args.manifest, SpeakingSample)
    paths = audio_paths(samples, args.audio_root)
    reports = []
    for model in args.models:
        config = WhisperConfig(model=model, device=args.device, compute_type=args.compute_type,
                               allow_download=args.allow_download)
        engine = FasterWhisperTranscriber(config)
        report = benchmark(samples, paths, engine)
        report.update(config=asdict(config), load_seconds=engine.load_seconds)
        reports.append(report)
        del engine
    write_report(args.output, {
        "schema_version": "asr-comparison.v1", "python": platform.python_version(),
        "platform": platform.system(), "processor": platform.processor(),
        "faster_whisper": importlib.metadata.version("faster-whisper"),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "runs": reports,
    })


if __name__ == "__main__":
    main()
