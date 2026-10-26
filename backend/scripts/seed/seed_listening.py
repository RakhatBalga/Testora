"""Seed the canonical versioned Testora Listening benchmark.

Run from backend/: python -m scripts.seed.seed_listening
"""
import argparse
import json
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.models.test import Test
from app.infrastructure.database import SessionLocal
from content_tools.importer import build_test
from content_tools.validate_listening import Report, validate_test


CONTENT_PATH = Path(__file__).resolve().parents[2] / "content/listening/testora-studio-02.json"


def _version(value: str) -> tuple[int, ...]:
    if value == "legacy":
        return (0, 0, 0)
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError(f"Expected a numeric major.minor.patch version, got {value!r}")
    return tuple(int(part) for part in value.split("."))


def seed_package(db: Session, data: dict, *, update_existing: bool = False) -> tuple[Test, bool]:
    """Append a version; keep existing question IDs, attempts and progress intact."""
    report = Report()
    validate_test(data, "Listening import", report)
    slug = (data.get("metadata") or {}).get("slug")
    if data.get("test_type") != "listening" or not slug or report.errors:
        raise ValueError("Invalid Listening package: " + "; ".join(report.errors or ["type or slug missing"]))
    incoming = build_test(data)
    if incoming.content_version == "legacy" or not (incoming.content_metadata or {}).get("published"):
        raise ValueError("A published package with an explicit content_version is required")
    version = _version(incoming.content_version)
    try:
        if db.get_bind().dialect.name == "postgresql":
            # Serialize the deployment command even when no version exists yet.
            db.execute(text("SELECT pg_advisory_xact_lock(82170422)"))
        candidates = db.query(Test).filter(Test.test_type == "listening").all()
        existing = [item for item in candidates if
                    (item.content_metadata or {}).get("slug") == slug or
                    (not (item.content_metadata or {}).get("slug") and item.title == incoming.title)]
        same = next((item for item in existing if item.content_version == incoming.content_version), None)
        if same is not None:
            db.commit()
            return same, False
        latest = max(existing, key=lambda item: _version(item.content_version), default=None)
        if latest is not None and not update_existing:
            db.commit()
            return latest, False
        if latest is not None and version <= _version(latest.content_version):
            raise ValueError("The replacement must have a newer content_version")
        db.add(incoming)
        db.flush()
        for old in existing:
            old.content_metadata = {**(old.content_metadata or {}), "superseded_by": incoming.id}
        db.commit()
        return incoming, True
    except BaseException:
        db.rollback()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Listening; preserve historical versions on update.")
    parser.add_argument("--update", action="store_true", help="Import a newer version without deleting attempts or progress")
    args = parser.parse_args()
    raw = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        test, created = seed_package(db, raw["tests"][0], update_existing=args.update)
        if created:
            print(f"Imported '{test.title}' version {test.content_version} (ID {test.id})")
        else:
            print(f"Kept '{test.title}' version {test.content_version}; use --update for a newer package")


if __name__ == "__main__":
    main()
