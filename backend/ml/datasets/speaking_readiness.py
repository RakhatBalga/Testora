"""Read-only preflight: python -m ml.datasets.speaking_readiness MANIFEST --audio-root DIR --output FILE.

Only aggregate diagnostics are exported. Pilot readiness is not statistical sufficiency.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from ml.benchmark_asr import audio_paths
from ml.data import SpeakingSample, read_jsonl, write_report
from ml.metrics import words


def assess(samples: list[SpeakingSample], audio_root: Path) -> dict:
    blockers, warnings = [], []
    speakers = len({s.speaker_id for s in samples})
    if speakers < 4:
        blockers.append("At least four speakers are required for the pilot split.")
    if len({s.sample_id for s in samples}) != len(samples):
        blockers.append("Duplicate sample IDs must be resolved.")
    if any(not words(s.reference_text) for s in samples):
        blockers.append("Some references have no English tokens after WER normalization.")
    audio_checked = False
    try:
        audio_paths(samples, audio_root)
        audio_checked = bool(samples)
    except (OSError, ValueError):
        blockers.append("Audio preflight failed: check missing, outside-root or duplicate recordings.")
    bands = Counter(str(s.expert_band) for s in samples)
    if len(bands) < 2:
        warnings.append("Only one expert band is represented; score variation cannot be evaluated.")
    llm_count = sum(s.llm_band is not None for s in samples)
    if llm_count < len(samples):
        warnings.append("LLM scores are incomplete; a matched holdout comparison may be unavailable.")
    warnings.append("Four speakers is only a software minimum; plan sample size and independent expert labeling.")
    return {
        "schema_version": "speaking-readiness.v1",
        "status": "blocked" if blockers else "pilot_with_warnings",
        "can_run_pilot": not blockers,
        "sample_count": len(samples),
        "speaker_count": speakers,
        "expert_band_distribution": dict(sorted(bands.items())),
        "llm_scores_available": llm_count,
        "audio_preflight_passed": audio_checked,
        "blockers": blockers,
        "warnings": warnings,
        "limitations": [
            "Does not decode audio or verify recording quality.",
            "Consent is declared in the manifest; retain supporting consent records privately.",
            "Passing preflight does not establish model quality or IELTS validity.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        samples = read_jsonl(args.manifest, SpeakingSample)
        report = assess(samples, args.audio_root)
        report["manifest_sha256"] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        write_report(args.output, report)
    except (OSError, ValueError) as exc:
        parser.error(f"Cannot inspect manifest or create report ({type(exc).__name__}). Check input and output paths.")
    print(json.dumps({key: report[key] for key in ("status", "sample_count", "speaker_count", "blockers")}))
    return 0 if report["can_run_pilot"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
