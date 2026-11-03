"""Private Speaking collection registry and blind expert worksheet.

One speaking-recording.v1 JSON object per line: sample_id, speaker_id, part (1–3),
task_id, audio_path relative to --audio-root, consent (boolean), consent_record_id
(private consent receipt code), recorded_at (ISO timestamp with timezone), and
optional reference_text (human verbatim transcript, including disfluencies).
Use pseudonymous codes, never names/emails. Keep receipts outside this registry.

From backend:
python -m ml.datasets.speaking.registry ml/data/registry.jsonl \
    --audio-root ml/data/audio --output ml/data/expert.csv

The worksheet contains no transcript, learner identity or model prediction.
It is still private: audio paths grant access to participant recordings.
Consent is declared, not independently verified. No database access or AI calls.
"""

import argparse
import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import Field, StrictBool, field_validator, model_validator

from ml.data import Record, read_jsonl

Code = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
CRITERIA = ("fluency_coherence", "lexical_resource", "grammatical_range_accuracy", "pronunciation")
IDENTITY_COLUMNS = ("sample_id", "part", "task_id", "audio_path", "audio_sha256")
LABEL_COLUMNS = (*IDENTITY_COLUMNS, "rater_id", *CRITERIA, "overall_band")


class Recording(Record):
    schema_version: Literal["speaking-recording.v1"] = "speaking-recording.v1"
    sample_id: Code
    speaker_id: Code
    part: int = Field(strict=True, ge=1, le=3)
    task_id: Code
    audio_path: str
    consent: StrictBool
    consent_record_id: Code | None = None
    recorded_at: datetime
    reference_text: str | None = None

    @field_validator("audio_path")
    @classmethod
    def relative_audio(cls, value):
        # Portable relative POSIX paths; disallow CSV formulas and traversal.
        import re

        if (
            not value
            or "\\" in value
            or any(
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", segment) or segment in (".", "..")
                for segment in value.split("/")
            )
        ):
            raise ValueError("Expected a safe relative audio path")
        if PurePosixPath(value).is_absolute():
            raise ValueError("Audio path must be relative")
        return value

    @field_validator("recorded_at")
    @classmethod
    def aware_time(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Recording timestamp requires a timezone")
        return value

    @field_validator("reference_text")
    @classmethod
    def transcript(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Use null for a transcript not yet prepared")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def consent_receipt(self):
        if self.consent and self.consent_record_id is None:
            raise ValueError("Consented recordings need a private consent receipt code")
        return self


def inspect_recordings(records: list[Recording], audio_root: Path) -> list[dict]:
    """Validate the entire batch before exposing any recordings to a rater."""
    if not records or len({r.sample_id for r in records}) != len(records):
        raise ValueError("Expected a nonempty registry with unique sample IDs")
    if any(not r.consent for r in records):
        raise ValueError("Batch contains recordings without research consent")
    root = audio_root.resolve()
    identities, fingerprints = [], set()
    for number, row in enumerate(sorted(records, key=lambda r: r.sample_id), 1):
        path = (root / row.audio_path).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Recording {number}: audio missing or outside audio root")
        if path.stat().st_size == 0:
            raise ValueError(f"Recording {number}: audio is empty")
        with path.open("rb") as handle:
            fingerprint = hashlib.file_digest(handle, "sha256").hexdigest()
        if fingerprint in fingerprints:
            raise ValueError("Duplicate audio content in registry")
        fingerprints.add(fingerprint)
        identities.append(
            dict(
                sample_id=row.sample_id,
                part=str(row.part),
                task_id=row.task_id,
                audio_path=row.audio_path,
                audio_sha256=fingerprint,
            )
        )
    return identities


def worksheet(records: list[Recording], audio_root: Path) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=LABEL_COLUMNS)
    writer.writeheader()
    writer.writerows(inspect_recordings(records, audio_root))
    return buffer.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        records = read_jsonl(args.registry, Recording)
        payload = worksheet(records, args.audio_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="") as handle:
            handle.write(payload)
    except (OSError, ValueError):
        parser.error("Cannot prepare worksheet: check registry, consent, audio and unused output path.")
    print(f"Expert worksheet created: {len(records)} recordings. Keep it private.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
