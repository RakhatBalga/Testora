"""Validate IELTS Listening content packs before import.

Scans content/listening/*.json and enforces the MVP quality bar:

  * each listening test has 4 sections and 40 questions
  * each section has either audio_url or a transcript in passage
  * every question has a unique order, known question_type, correct_answer,
    explanation, and transcript evidence where practical
  * evidence quotes appear verbatim in the section transcript

Exit code 0 = all checks passed; 1 = one or more failures.

Run from backend/:  python validate_listening.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "content" / "listening"
EXPECTED_SECTIONS = 4
EXPECTED_QUESTIONS = 40
QUESTION_TYPES = {
    "single_choice",
    "multiple_choice",
    "true_false_notgiven",
    "yes_no_not_given",
    "matching",
    "matching_headings",
    "matching_information",
    "sentence_completion",
    "summary_completion",
    "fill_blank",
    "short_answer",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.tests = 0
        self.questions = 0

    def err(self, msg: str) -> None:
        self.errors.append(msg)


def _spans(raw) -> list[dict]:
    if not raw:
        return []
    return raw if isinstance(raw, list) else [raw]


def validate_test(data: dict, where: str, rep: Report) -> None:
    if data.get("test_type") != "listening":
        return
    rep.tests += 1
    title = data.get("title", where)
    sections = data.get("sections", [])
    if len(sections) != EXPECTED_SECTIONS:
        rep.err(f"{title}: expected {EXPECTED_SECTIONS} sections, found {len(sections)}")

    seen_orders: set[int] = set()
    total_q = 0
    for index, section in enumerate(sections, 1):
        label = f"{title} · Section {section.get('order', index)}"
        transcript = section.get("passage") or ""
        if not section.get("audio_url") and not transcript.strip():
            rep.err(f"{label}: missing audio_url and transcript")
        if not transcript.strip():
            rep.err(f"{label}: missing transcript in passage")

        questions = section.get("questions", [])
        total_q += len(questions)
        if len(questions) != 10:
            rep.err(f"{label}: {len(questions)} questions (expected 10)")

        norm_transcript = _norm(transcript)
        for q in questions:
            rep.questions += 1
            order = q.get("order")
            qid = f"{title} · Q{order or '?'}"
            if not isinstance(order, int):
                rep.err(f"{qid}: order must be an integer")
            elif order in seen_orders:
                rep.err(f"{qid}: duplicate question order")
            else:
                seen_orders.add(order)

            qtype = q.get("question_type")
            if qtype not in QUESTION_TYPES:
                rep.err(f"{qid}: unknown question_type '{qtype}'")
            if not q.get("text"):
                rep.err(f"{qid}: missing text")
            answers = q.get("correct_answer")
            if not answers or not isinstance(answers, list):
                rep.err(f"{qid}: missing/invalid correct_answer")
            if not q.get("explanation"):
                rep.err(f"{qid}: missing explanation")
            if qtype in {
                "single_choice",
                "multiple_choice",
                "true_false_notgiven",
                "yes_no_not_given",
                "matching",
                "matching_headings",
                "matching_information",
            } and not q.get("options"):
                rep.err(f"{qid}: options required for {qtype}")

            spans = _spans(q.get("evidence"))
            if not spans:
                rep.err(f"{qid}: missing transcript evidence")
                continue
            for span in spans:
                quote = span.get("quote", span.get("text"))
                if not quote:
                    rep.err(f"{qid}: evidence missing quote")
                    continue
                if norm_transcript and _norm(quote) not in norm_transcript:
                    rep.err(f"{qid}: evidence quote not found in transcript: \"{quote[:60]}...\"")

    if total_q != EXPECTED_QUESTIONS:
        rep.err(f"{title}: {total_q} questions total (expected {EXPECTED_QUESTIONS})")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate IELTS Listening content packs.")
    parser.add_argument("--files", nargs="+", metavar="PATH", help="Validate only these files.")
    args = parser.parse_args()

    rep = Report()
    files = [Path(f) for f in args.files] if args.files else sorted(CONTENT_DIR.glob("*.json"))
    if not files:
        print(f"No listening content files found in {CONTENT_DIR}")
        return 1

    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            rep.err(f"{path.name}: cannot read ({exc})")
            continue
        for test in raw.get("tests", []):
            validate_test(test, path.name, rep)

    print("Listening content validation")
    print(f"  files scanned : {len(files)}")
    print(f"  listening tests: {rep.tests}")
    print(f"  questions     : {rep.questions}")
    if rep.errors:
        print(f"\n  {len(rep.errors)} issue(s):")
        for error in rep.errors:
            print(f"   x {error}")
        return 1
    print("\n  all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
