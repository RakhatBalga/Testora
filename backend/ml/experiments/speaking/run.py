"""Run the private Speaking pipeline. See USAGE.txt beside this module."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from html import escape
import importlib.metadata
import json
from pathlib import Path
import platform

from ml.asr import FasterWhisperTranscriber, WhisperConfig
from ml.benchmark_asr import audio_paths, benchmark
from ml.data import SpeakingSample, read_jsonl, write_report
from ml.datasets.speaking.readiness import assess
from ml.train_speaking import speaker_split, train_compare


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def versions():
    result = {"python": platform.python_version(), "platform": platform.system()}
    for name in ("numpy", "scikit-learn", "joblib", "faster-whisper", "ctranslate2"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def render_summary(report):
    """An aggregate-only HTML companion; JSON remains private and pseudonymous."""
    rows = []
    for name, metrics in report["experiment"]["models"].items():
        values = []
        for key in ("mae", "qwk", "within_half_band"):
            value = metrics.get(key)
            values.append("n/a" if value is None else f"{value:.3f}")
        rows.append("<tr><td>" + escape(name) + "</td>" + "".join(f"<td>{v}</td>" for v in values) + "</tr>")
    exp = report["experiment"]
    warnings = report["readiness"]["warnings"] + exp["limitations"]
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Speaking pilot</title>'
        "<style>body{font:16px/1.6 system-ui;max-width:950px;margin:40px auto;padding:20px}"
        "td,th{border:1px solid #ccd;padding:10px}table{border-collapse:collapse}</style><main>"
        f"<h1>Speaking pilot — {escape(report['dataset_kind'])} data</h1>"
        "<p>This is an experimental comparison, not an official IELTS assessment. "
        "Synthetic results verify software only; they are not evidence of accuracy on real learners.</p>"
        f"<p>Samples: {report['readiness']['sample_count']}; speakers: {report['readiness']['speaker_count']}. "
        f"Train: {exp['train_count']} samples / {len(exp['train_speakers'])} speakers; "
        f"holdout: {exp['test_count']} samples / {len(exp['test_speakers'])} speakers.</p>"
        f"<p>Seed: {exp['seed']}; holdout fraction: {exp['test_size']}; "
        f"ASR model: {escape(report['config']['model'])}. "
        f"Corpus WER (all recordings): {report['asr']['corpus_wer']:.3f}.</p>"
        "<table><tr><th>Model</th><th>MAE ↓</th><th>QWK ↑</th><th>Within 0.5 band ↑</th></tr>"
        + "".join(rows)
        + "</table><p>Metrics use the same held-out speakers. n/a means undefined "
        "QWK or missing LLM scores, not zero error. No model is selected using the holdout.</p><ul>"
        + "".join(f"<li>{escape(w)}</li>" for w in warnings)
        + "</ul><p>Dataset kind and consent are declared, not independently verified. "
        "ASR output is not used as a human reference transcript.</p></main></html>"
    )


def run_experiment(
    manifest,
    audio_root,
    output_dir,
    *,
    config,
    dataset_kind,
    seed=42,
    test_size=0.25,
    check_only=False,
    engine_factory=FasterWhisperTranscriber,
):
    if dataset_kind not in {"real", "synthetic"}:
        raise ValueError("Explicit real or synthetic dataset kind required")
    # Validate everything inexpensive before creating outputs or loading a model.
    manifest_hash = digest(manifest)
    samples = sorted(read_jsonl(manifest, SpeakingSample), key=lambda s: (s.speaker_id, s.sample_id))
    readiness = assess(samples, audio_root)
    if not readiness["can_run_pilot"]:
        raise ValueError("Dataset preflight failed; use the Speaking readiness tool for aggregate diagnostics")
    train, test = speaker_split(samples, seed=seed, test_size=test_size)
    paths = audio_paths(samples, audio_root)
    if any(p.stat().st_size == 0 for p in paths):
        raise ValueError("Audio contains an empty file")
    hashes = {s.sample_id: digest(p) for s, p in zip(samples, paths)}
    config_data = asdict(config)
    # A local model path may identify the workstation; retain only its name.
    config_data["model"] = Path(config.model).name
    source_files = [
        Path(__file__),
        Path(__file__).parents[2] / "train_speaking.py",
        Path(__file__).parents[2] / "benchmark_asr.py",
        Path(__file__).parents[2] / "asr.py",
        Path(__file__).parents[2] / "speech_features.py",
        Path(__file__).parents[2] / "metrics.py",
    ]
    metadata = {
        "schema_version": "speaking-run.v1",
        "dataset_kind": dataset_kind,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": manifest_hash,
        "audio_sha256": hashes,
        "config": config_data,
        "seed": seed,
        "test_size": test_size,
        "environment": versions(),
        "source_sha256": {p.name: digest(p) for p in source_files},
        "readiness": readiness,
        "planned_split": {
            name: [samples[i].sample_id for i in ids] for name, ids in (("train", train), ("holdout", test))
        },
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    write_report(output_dir / "run.json", metadata)
    if check_only:
        write_report(output_dir / "status.json", {"status": "preflight_only", "models_trained": False})
        return metadata
    try:
        engine = engine_factory(config)
        asr = benchmark(samples, paths, engine)
        if digest(manifest) != manifest_hash or hashes != {s.sample_id: digest(p) for s, p in zip(samples, paths)}:
            raise ValueError("Input changed during ASR; discard the run and retry with immutable inputs")
        write_report(output_dir / "asr.json", asr)
        experiment = train_compare(asr["samples"], seed=seed, test_size=test_size, artifacts=output_dir / "models")
        if experiment["split_samples"] != metadata["planned_split"]:
            raise ValueError("Training split differs from the predeclared holdout")
        report = {**metadata, "asr": asr, "experiment": experiment}
        write_report(output_dir / "report.json", report)
        (output_dir / "summary.html").write_text(render_summary(report), encoding="utf-8")
        write_report(output_dir / "status.json", {"status": "completed", "models_trained": True})
        return report
    except Exception:
        # No exception text: ASR/library errors can contain paths or transcripts.
        write_report(output_dir / "status.json", {"status": "failed", "results_usable": False})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="New private directory; never overwritten")
    parser.add_argument("--dataset-kind", choices=["real", "synthetic"], required=True)
    parser.add_argument("--model", default="tiny.en")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        run_experiment(
            args.manifest,
            args.audio_root,
            args.output_dir,
            config=WhisperConfig(
                model=args.model, device=args.device, compute_type=args.compute_type, allow_download=args.allow_download
            ),
            dataset_kind=args.dataset_kind,
            seed=args.seed,
            test_size=args.test_size,
            check_only=args.check_only,
        )
    except Exception:
        parser.exit(
            2, "Speaking run failed. Check private input, dependencies, local model and unused output directory.\n"
        )
    print(
        json.dumps({"status": "preflight_only" if args.check_only else "completed", "dataset_kind": args.dataset_kind})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
