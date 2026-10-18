"""Export submitted Reading/Listening outcomes for adaptive experiments.

From backend: python -m ml.export_responses --output ml/data/responses.jsonl
Set ML_EXPORT_KEY to a private random secret of at least 32 UTF-8 bytes.
Reuse it for exports from the same study/database to keep pseudonyms stable.
Use a different key for unrelated datasets. Never commit the key or exports.

No names, email addresses, answer text or answer keys are exported. Repeated
attempts and unanswered questions are retained; evaluate_adaptive excludes
repeats itself. answered_at is submission time, not per-question response time.
Legacy versions are preserved, never inferred from today's content version.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path

from ml.data import ResponseRecord


def utc(value: datetime) -> datetime:
    # Database timestamps are stored as naive UTC by the application.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def export_records(db, *, secret: str, skill: str | None = None,
                   since: datetime | None = None, until: datetime | None = None,
                   mode: str | None = None, exclude_legacy: bool = False):
    """Read only. Return validated response.v1 rows plus aggregate provenance."""
    from sqlalchemy import select
    from app.domain.models.attempt import AnswerRecord, Attempt
    from app.domain.models.test import Test, Section, Question

    if len(secret.encode("utf-8")) < 32:
        raise ValueError("ML_EXPORT_KEY must contain at least 32 UTF-8 bytes")
    if skill not in {None, "reading", "listening"} or mode not in {None, "exam", "practice"}:
        raise ValueError("Unsupported skill or mode")
    if any(value is not None and value.utcoffset() is None for value in (since, until)):
        raise ValueError("Date filters require an explicit timezone")
    if since and until and since >= until:
        raise ValueError("--since must precede --until")

    def pseudonym(kind, identifier):
        return hmac.new(secret.encode("utf-8"), f"{kind}:{identifier}".encode(), hashlib.sha256).hexdigest()

    query = (select(AnswerRecord.id, Attempt.user_id, Attempt.test_id,
                    AnswerRecord.question_id, Attempt.content_version,
                    Test.test_type, Question.question_type, AnswerRecord.is_correct,
                    Attempt.created_at, Attempt.mode, Section.test_id.label("question_test_id"))
             .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
             .join(Test, Attempt.test_id == Test.id)
             .join(Question, AnswerRecord.question_id == Question.id)
             .join(Section, Question.section_id == Section.id)
             .where(Test.test_type.in_(["reading", "listening"]))
             .order_by(Attempt.created_at, Attempt.id, AnswerRecord.id))
    if skill:
        query = query.where(Test.test_type == skill)
    if mode:
        query = query.where(Attempt.mode == mode)
    if since:
        query = query.where(Attempt.created_at >= utc(since).replace(tzinfo=None))
    if until:
        query = query.where(Attempt.created_at < utc(until).replace(tzinfo=None))
    if exclude_legacy:
        query = query.where(Attempt.content_version != "legacy")
    records, skills, modes = [], Counter(), Counter()
    legacy = 0
    for row in db.execute(query.execution_options(autoflush=False)):
        if row.question_test_id != row.test_id:
            raise ValueError("An answer references a question from another test; export stopped")
        if row.created_at is None:
            raise ValueError("A submission has no timestamp; export stopped")
        records.append(ResponseRecord(
            response_id=pseudonym("response", row.id),
            learner_id=pseudonym("learner", row.user_id),
            item_id=f"test:{row.test_id}:question:{row.question_id}",
            content_version=row.content_version, skill=row.test_type,
            question_type=row.question_type, correct=row.is_correct,
            answered_at=utc(row.created_at),
        ))
        skills[row.test_type] += 1
        modes[row.mode] += 1
        legacy += int(row.content_version == "legacy")
    metadata = {
        "schema_version": "response-export.v1", "record_count": len(records),
        "learner_count": len({r.learner_id for r in records}),
        "item_count": len({r.item_key for r in records}),
        "records_by_skill": dict(skills), "records_by_mode": dict(modes),
        "legacy_record_count": legacy,
        "filters": {"skill": skill, "mode": mode, "exclude_legacy": exclude_legacy,
                    "since_inclusive": since.isoformat() if since else None,
                    "until_exclusive": until.isoformat() if until else None},
        "limitations": [
            "answered_at is submission time; question-level response times are unavailable.",
            "Repeated attempts and unanswered questions (scored incorrect) are retained.",
            "Legacy content has no reliable version snapshot; historical question types use current rows.",
            "Practice and exam modes may be mixed unless --mode is selected.",
            "Pseudonymous records are research data, not guaranteed anonymous data.",
        ],
    }
    return records, metadata


def write_export(output: Path, records: list[ResponseRecord], metadata: dict):
    if not records:
        raise ValueError("No matching submitted answers; no export was written")
    report_path = output.with_name(output.name + ".meta.json")
    if output.exists() or report_path.exists():
        raise FileExistsError("Export or metadata file already exists; choose a new output path")
    payload = "".join(record.model_dump_json() + "\n" for record in records).encode("utf-8")
    report = {**metadata, "dataset_sha256": hashlib.sha256(payload).hexdigest(),
              "exported_at": datetime.now(timezone.utc).isoformat()}
    output.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        with output.open("xb") as handle:
            created.append(output)
            handle.write(payload)
        with report_path.open("x", encoding="utf-8") as handle:
            created.append(report_path)
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return report


def date_filter(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError()
        return parsed
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use ISO 8601 with timezone, e.g. 2026-10-01T00:00:00Z") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skill", choices=["reading", "listening"])
    parser.add_argument("--mode", choices=["exam", "practice"])
    parser.add_argument("--since", type=date_filter)
    parser.add_argument("--until", type=date_filter)
    parser.add_argument("--exclude-legacy", action="store_true")
    args = parser.parse_args()
    secret = os.environ.get("ML_EXPORT_KEY", "")
    if len(secret.encode("utf-8")) < 32:
        parser.error("Set ML_EXPORT_KEY to a private secret of at least 32 UTF-8 bytes")
    from sqlalchemy import text
    from app.infrastructure.database import SessionLocal
    try:
        with SessionLocal() as db:
            if db.get_bind().dialect.name == "postgresql":
                db.execute(text("SET TRANSACTION READ ONLY"))
            records, metadata = export_records(db, secret=secret, skill=args.skill,
                mode=args.mode, since=args.since, until=args.until, exclude_legacy=args.exclude_legacy)
        report = write_export(args.output, records, metadata)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: report[key] for key in ("record_count", "learner_count", "legacy_record_count", "dataset_sha256")}))


if __name__ == "__main__":
    main()
