"""Import IELTS practice materials from JSON files into the database.

This is the recommended way to add practice content sourced from elsewhere
(Cambridge IELTS books, your own authored material, etc.). Unlike seed.py,
which hard-codes a couple of demo tests, this reads every *.json file in the
content/ folder so you can grow the question bank just by dropping in files.

Usage (run from the backend/ folder, venv active):

    python import_content.py                 # import everything in content/
    python import_content.py content/foo.json  # import specific file(s)
    python import_content.py --replace       # overwrite items with the same key

Safety:
    * By default existing items are SKIPPED (matched by a natural key), so the
      script is safe to re-run and never touches user submissions/attempts.
    * --replace deletes the matching item first, then re-creates it. It refuses
      to delete anything that already has user submissions/attempts attached.

JSON shape (any of the three arrays may be present per file):

    {
      "tests": [
        {
          "title": "Academic Reading Practice 2",
          "test_type": "reading",            # "reading" | "listening"
          "description": "...",
          "duration_minutes": 20,
          "sections": [
            {
              "order": 1,
              "title": "Section 1 — ...",
              "instructions": "...",
              "passage": "...",               # reading text (omit for listening)
              "audio_url": "https://.../clip.mp3",  # listening audio (omit for reading)
              "questions": [
                {
                  "order": 1,
                  "text": "...",
                  "question_type": "single_choice",
                  "options": ["A", "B", "C", "D"],   # null for free-text types
                  "correct_answer": ["A"]            # list of acceptable answers
                }
              ]
            }
          ]
        }
      ],
      "writing_tasks": [
        {
          "task_type": 1,                     # 1 or 2
          "title": "Writing Task 1 — Line graph",
          "prompt": "...",
          "image_url": "/static/charts/graph1.png",  # or null
          "min_words": 150,
          "duration_minutes": 20
        }
      ],
      "speaking_tasks": [
        {
          "part": 1,                          # 1, 2 or 3
          "questions": ["...", "..."],
          "prep_seconds": 15,
          "speak_seconds": 60
        }
      ]
    }
"""
import json
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models.test import Test, Section, Question
from app.models.attempt import Attempt
from app.models.writing import WritingTask, WritingSubmission
from app.models.speaking import SpeakingTask, SpeakingSubmission

CONTENT_DIR = Path(__file__).resolve().parent / "content"

QUESTION_TYPES = {
    "single_choice",
    "multiple_choice",
    "true_false_notgiven",
    "matching",
    "fill_blank",
    "short_answer",
}


class ImportError_(Exception):
    """Raised when a JSON file is structurally invalid."""


def _require(obj: dict, key: str, where: str):
    if key not in obj:
        raise ImportError_(f"Missing required field '{key}' in {where}")
    return obj[key]


# --------------------------------------------------------------------------- #
# Builders: turn a plain dict into an ORM object (no DB writes here)
# --------------------------------------------------------------------------- #
def _build_test(data: dict) -> Test:
    title = _require(data, "title", "test")
    test_type = _require(data, "test_type", f"test '{title}'")
    if test_type not in ("reading", "listening"):
        raise ImportError_(
            f"test '{title}': test_type must be 'reading' or 'listening', got '{test_type}'"
        )

    test = Test(
        title=title,
        test_type=test_type,
        description=data.get("description"),
        duration_minutes=int(data.get("duration_minutes", 30)),
        difficulty=data.get("difficulty"),
    )

    sections = _require(data, "sections", f"test '{title}'")
    test.sections = [_build_section(s, title, i) for i, s in enumerate(sections, 1)]
    return test


def _build_section(data: dict, test_title: str, default_order: int) -> Section:
    where = f"test '{test_title}', section {default_order}"
    section = Section(
        order=int(data.get("order", default_order)),
        title=_require(data, "title", where),
        instructions=data.get("instructions"),
        passage=data.get("passage"),
        audio_url=data.get("audio_url"),
    )
    questions = _require(data, "questions", where)
    section.questions = [
        _build_question(q, where, i) for i, q in enumerate(questions, 1)
    ]
    return section


def _build_question(data: dict, where: str, default_order: int) -> Question:
    q_type = _require(data, "question_type", f"{where}, question {default_order}")
    if q_type not in QUESTION_TYPES:
        raise ImportError_(
            f"{where}, question {default_order}: unknown question_type '{q_type}'. "
            f"Allowed: {', '.join(sorted(QUESTION_TYPES))}"
        )
    correct = _require(data, "correct_answer", f"{where}, question {default_order}")
    if not isinstance(correct, list):
        raise ImportError_(
            f"{where}, question {default_order}: correct_answer must be a list"
        )
    return Question(
        order=int(data.get("order", default_order)),
        text=_require(data, "text", f"{where}, question {default_order}"),
        question_type=q_type,
        options=data.get("options"),
        correct_answer=correct,
        explanation=data.get("explanation"),
        evidence=_normalize_evidence(data.get("evidence")),
    )


def _normalize_evidence(raw):
    """Accept a single span or a list of {paragraph, sentence, quote} and store
    the frontend-compatible shape [{paragraph, sentence, text}] (text = quote)."""
    if not raw:
        return None
    spans = raw if isinstance(raw, list) else [raw]
    out = []
    for e in spans:
        quote = e.get("quote", e.get("text"))
        if e.get("paragraph") is None or not quote:
            continue
        out.append(
            {"paragraph": e["paragraph"], "sentence": e.get("sentence"), "text": quote}
        )
    return out or None


def _build_writing(data: dict) -> WritingTask:
    title = _require(data, "title", "writing_task")
    return WritingTask(
        task_type=int(_require(data, "task_type", f"writing_task '{title}'")),
        title=title,
        prompt=_require(data, "prompt", f"writing_task '{title}'"),
        image_url=data.get("image_url"),
        min_words=int(data.get("min_words", 250)),
        duration_minutes=int(data.get("duration_minutes", 40)),
    )


def _build_speaking(data: dict) -> SpeakingTask:
    questions = _require(data, "questions", "speaking_task")
    if not isinstance(questions, list) or not questions:
        raise ImportError_("speaking_task: 'questions' must be a non-empty list")
    return SpeakingTask(
        part=int(_require(data, "part", "speaking_task")),
        questions=questions,
        prep_seconds=int(data.get("prep_seconds", 60)),
        speak_seconds=int(data.get("speak_seconds", 120)),
    )


# --------------------------------------------------------------------------- #
# Import logic
# --------------------------------------------------------------------------- #
def _import_file(db, path: Path, replace: bool, stats: dict):
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ImportError_(f"{path.name}: top level must be a JSON object")

    for data in raw.get("tests", []):
        test = _build_test(data)
        existing = db.query(Test).filter(Test.title == test.title).first()
        if existing:
            if not replace:
                stats["skipped"] += 1
                print(f"  skip  test    '{test.title}' (already exists)")
                continue
            if db.query(Attempt).filter(Attempt.test_id == existing.id).first():
                stats["blocked"] += 1
                print(f"  KEEP  test    '{test.title}' (has user attempts, not replaced)")
                continue
            db.delete(existing)
            db.flush()
        db.add(test)
        stats["added"] += 1
        print(f"  add   test    '{test.title}' ({test.test_type})")

    for data in raw.get("writing_tasks", []):
        task = _build_writing(data)
        existing = db.query(WritingTask).filter(WritingTask.title == task.title).first()
        if existing:
            if not replace:
                stats["skipped"] += 1
                print(f"  skip  writing '{task.title}' (already exists)")
                continue
            if (
                db.query(WritingSubmission)
                .filter(WritingSubmission.task_id == existing.id)
                .first()
            ):
                stats["blocked"] += 1
                print(f"  KEEP  writing '{task.title}' (has submissions, not replaced)")
                continue
            db.delete(existing)
            db.flush()
        db.add(task)
        stats["added"] += 1
        print(f"  add   writing '{task.title}' (Task {task.task_type})")

    for data in raw.get("speaking_tasks", []):
        task = _build_speaking(data)
        first_q = task.questions[0]
        existing = (
            db.query(SpeakingTask)
            .filter(SpeakingTask.part == task.part)
            .all()
        )
        match = next((t for t in existing if (t.questions or [None])[0] == first_q), None)
        if match:
            if not replace:
                stats["skipped"] += 1
                print(f"  skip  speak   Part {task.part} '{first_q[:40]}...' (exists)")
                continue
            if (
                db.query(SpeakingSubmission)
                .filter(SpeakingSubmission.task_id == match.id)
                .first()
            ):
                stats["blocked"] += 1
                print(f"  KEEP  speak   Part {task.part} (has submissions, not replaced)")
                continue
            db.delete(match)
            db.flush()
        db.add(task)
        stats["added"] += 1
        print(f"  add   speak   Part {task.part} '{first_q[:40]}...'")


def run(paths: list[Path], replace: bool):
    if not paths:
        print(f"No JSON files found in {CONTENT_DIR}")
        return

    db = SessionLocal()
    stats = {"added": 0, "skipped": 0, "blocked": 0}
    try:
        for path in paths:
            print(f"\n{path.name}:")
            _import_file(db, path, replace, stats)
        db.commit()
    except (ImportError_, json.JSONDecodeError) as exc:
        db.rollback()
        print(f"\nImport aborted (no changes saved): {exc}")
        sys.exit(1)
    finally:
        db.close()

    print(
        f"\nDone. added={stats['added']} skipped={stats['skipped']} "
        f"blocked={stats['blocked']}"
    )


def _collect_paths(args: list[str]) -> list[Path]:
    files = [a for a in args if not a.startswith("--")]
    if files:
        return [Path(f) for f in files]
    if not CONTENT_DIR.exists():
        return []
    return sorted(CONTENT_DIR.glob("*.json"))


if __name__ == "__main__":
    replace_flag = "--replace" in sys.argv
    run(_collect_paths(sys.argv[1:]), replace_flag)
