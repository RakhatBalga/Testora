"""Seed the canonical versioned Testora Listening benchmark.

Run from backend/: .venv/bin/python seed_listening.py
"""
import json
from pathlib import Path

from app.domain.models.test import Test
from app.infrastructure.database import SessionLocal
from import_content import _build_test


CONTENT_PATH = Path(__file__).resolve().parent / "content/listening/testora-studio-01.json"


def main() -> None:
    raw = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    test = _build_test(raw["tests"][0])
    db = SessionLocal()
    try:
        if db.query(Test).filter(Test.title == test.title).first():
            print(f"'{test.title}' already exists - skipped")
            return
        db.add(test)
        db.commit()
        print(f"Seeded '{test.title}' with 4 sections and 40 questions")
    finally:
        db.close()


if __name__ == "__main__":
    main()
