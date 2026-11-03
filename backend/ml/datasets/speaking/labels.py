"""Import a completed expert worksheet and build a private speaking.v1 bundle.

From backend:
python -m ml.datasets.speaking.labels ml/data/registry.jsonl ml/data/expert.csv \
    --audio-root ml/data/audio --output-dir ml/data/labeled-run-001

Fill rater_id (pseudonymous code), fluency_coherence, lexical_resource,
grammatical_range_accuracy, pronunciation and overall_band in the worksheet.
All scores must be half bands in [0, 9]. Overall is the expert's independent
assessment of this recording: it is neither computed nor an official exam score.
Exactly one final rating per recording is supported; adjudicate disagreements
outside this importer, retaining the original ratings privately.

The new output directory contains samples.jsonl (for speaking_readiness and
benchmark_asr), labels.jsonl (criterion scores and rater provenance), metadata.json
(input hashes and counts). reference_text must be a human verbatim transcript.
Use the SAME audio root with downstream commands. No audio is copied or uploaded.
"""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from ml.data import Record, SpeakingSample, read_jsonl
from ml.datasets.speaking.registry import (
    CRITERIA,
    IDENTITY_COLUMNS,
    LABEL_COLUMNS,
    Code,
    Recording,
    inspect_recordings,
)
from ml.metrics import words

Band = Annotated[float, Field(ge=0, le=9, multiple_of=0.5)]


class ExpertRating(Record):
    schema_version: Literal["speaking-rating.v1"] = "speaking-rating.v1"
    sample_id: Code
    rater_id: Code
    fluency_coherence: Band
    lexical_resource: Band
    grammatical_range_accuracy: Band
    pronunciation: Band
    overall_band: Band


def import_ratings(payload: str, identities: list[dict]) -> list[ExpertRating]:
    expected = {row["sample_id"]: row for row in identities}
    reader = csv.DictReader(io.StringIO(payload.lstrip("\ufeff")), strict=True)
    if reader.fieldnames != list(LABEL_COLUMNS):
        raise ValueError("Worksheet columns changed; use the generated template")
    ratings, seen = [], set()
    try:
        for row in reader:
            number = reader.line_num
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Malformed CSV row")
                sample_id = row["sample_id"]
                if sample_id not in expected or sample_id in seen:
                    raise ValueError("Unknown or repeated sample")
                if any(row[key] != expected[sample_id][key] for key in IDENTITY_COLUMNS):
                    raise ValueError("Recording metadata changed")
                rating = ExpertRating.model_validate(
                    {
                        "sample_id": sample_id,
                        **{key: row[key].strip() for key in ("rater_id", *CRITERIA, "overall_band")},
                    }
                )
                seen.add(sample_id)
                ratings.append(rating)
            except ValueError:
                raise ValueError(f"Invalid or mismatched expert rating at CSV line {number}") from None
    except csv.Error:
        raise ValueError("Malformed expert worksheet CSV") from None
    if seen != set(expected) or not ratings:
        raise ValueError("Every registry recording needs exactly one complete expert rating")
    return sorted(ratings, key=lambda r: r.sample_id)


def assemble(records: list[Recording], ratings: list[ExpertRating]) -> list[SpeakingSample]:
    if not records or len({r.sample_id for r in records}) != len(records):
        raise ValueError("Registry must contain unique recordings")
    labels = {r.sample_id: r for r in ratings}
    if len(labels) != len(ratings) or set(labels) != {r.sample_id for r in records}:
        raise ValueError("Ratings must match the registry exactly")
    samples = []
    for index, row in enumerate(sorted(records, key=lambda r: r.sample_id), 1):
        if not row.consent or not row.consent_record_id:
            raise ValueError("Research consent is required for every recording")
        if row.reference_text is None or not words(row.reference_text):
            raise ValueError(f"Recording {index} needs a usable human reference transcript")
        samples.append(
            SpeakingSample(
                sample_id=row.sample_id,
                speaker_id=row.speaker_id,
                audio_path=row.audio_path,
                reference_text=row.reference_text,
                expert_band=labels[row.sample_id].overall_band,
                consent=True,
            )
        )
    return samples


def build_bundle(registry: Path, worksheet: Path, audio_root: Path, output_dir: Path) -> dict:
    # Validate everything before creating output; no partial dataset on input errors.
    registry_bytes, worksheet_bytes = registry.read_bytes(), worksheet.read_bytes()
    records = read_jsonl(registry, Recording)
    if registry.read_bytes() != registry_bytes:
        raise ValueError("Registry changed during import; retry with a stable file")
    identities = inspect_recordings(records, audio_root)
    ratings = import_ratings(worksheet_bytes.decode("utf-8-sig"), identities)
    samples = assemble(records, ratings)
    metadata = {
        "schema_version": "speaking-collection-bundle.v1",
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "worksheet_sha256": hashlib.sha256(worksheet_bytes).hexdigest(),
        "recording_count": len(samples),
        "speaker_count": len({s.speaker_id for s in samples}),
        "rater_count": len({r.rater_id for r in ratings}),
        "part_counts": {str(part): sum(r.part == part for r in records) for part in (1, 2, 3)},
        "rating_policy": "one_final_human_rating_per_recording",
        "limitations": [
            "No inter-rater agreement measured by this import.",
            "Individual recording scores are not official full-test IELTS scores.",
            "Audio existence and identity checked; decoding and expert qualifications not verified.",
            "Research consent declared in registry; keep supporting records privately.",
        ],
    }
    # Preserve task/part and audio identity alongside expert labels, without raw transcripts.
    identity_by_id = {r["sample_id"]: r for r in identities}
    label_rows = [{**r.model_dump(), "recording": identity_by_id[r.sample_id]} for r in ratings]
    payloads = {
        "samples.jsonl": "".join(r.model_dump_json() + "\n" for r in samples),
        "labels.jsonl": "".join(json.dumps(r, allow_nan=False) + "\n" for r in label_rows),
        "metadata.json": json.dumps(metadata, indent=2, allow_nan=False) + "\n",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        for filename, payload in payloads.items():
            with (output_dir / filename).open("x", encoding="utf-8") as handle:
                handle.write(payload)
    except OSError:
        # Only remove files created in our newly reserved directory.
        for filename in payloads:
            (output_dir / filename).unlink(missing_ok=True)
        output_dir.rmdir()
        raise
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("registry", type=Path)
    parser.add_argument("worksheet", type=Path)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_bundle(args.registry, args.worksheet, args.audio_root, args.output_dir)
    except (OSError, ValueError):
        parser.error(
            "Import failed: check consent, transcripts, unchanged worksheet metadata, complete scores and a new output directory."
        )
    print(json.dumps({k: result[k] for k in ("recording_count", "speaker_count", "rater_count")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
