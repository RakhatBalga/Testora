"""Validate Academic Reading content packs before import.

Scans content/reading/*.json and enforces the production quality bar:

  * exactly EXPECTED_TESTS reading tests
  * exactly 3 passages per test, with 13 / 13 / 14 questions (40 total)
  * passage word counts within target ranges
  * total text length within the official Academic Reading range (2150-2750)
  * every question has correct_answer + explanation
  * every question (except a "Not Given" answer) has evidence with
    paragraph + sentence + quote, and the quote appears verbatim in the passage
    (after whitespace normalisation and stripping **highlight** markers)
  * no placeholder / demo content

Exit code 0 = all checks passed; 1 = one or more failures.

Run from backend/:  venv/bin/python validate_reading.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "content" / "reading"
EXPECTED_TESTS = 10
QCOUNTS = [13, 13, 14]
WORD_RANGES = [(800, 900), (900, 1000), (950, 1100)]
TOTAL_WORD_RANGE = (2150, 2750)
PLACEHOLDER_PATTERNS = re.compile(r"\b(lorem ipsum|todo|fixme|placeholder|xxxx|tbd)\b", re.I)
NOT_GIVEN = {"not given", "notgiven"}
POLARITY_ANSWERS = {
    "true_false_notgiven": {"true", "false", "not given"},
    "yes_no_not_given": {"yes", "no", "not given"},
}
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
    """Lowercase, strip ** markers and collapse whitespace for verbatim checks."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip().lower()


def _word_count(passage: str) -> int:
    # Drop paragraph markers (¶A / ¶1) and ** markers, then count words.
    cleaned = re.sub(r"¶\S+", " ", passage).replace("**", "")
    return len(re.findall(r"[A-Za-z0-9']+", cleaned))


def _passage_text(section: dict) -> str:
    if "passage" in section:
        return section["passage"]
    # Support a structured "paragraphs" list too.
    return "\n\n".join(p.get("text", "") for p in section.get("paragraphs", []))


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.tests = 0
        self.questions = 0
        self.p_words: list[int] = []
        self.t_words: list[int] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)


def validate_test(data: dict, where: str, rep: Report) -> None:
    if data.get("test_type") != "reading":
        return
    rep.tests += 1
    title = data.get("title", where)
    sections = data.get("sections", [])
    if len(sections) != 3:
        rep.err(f"{title}: expected 3 passages, found {len(sections)}")
        return

    total_q = 0
    total_words = 0
    for i, section in enumerate(sections):
        passage = _passage_text(section)
        wc = _word_count(passage)
        total_words += wc
        rep.p_words.append(wc)
        lo, hi = WORD_RANGES[i]
        if not (lo <= wc <= hi):
            rep.err(f"{title} · Passage {i+1}: {wc} words (target {lo}-{hi})")
        if PLACEHOLDER_PATTERNS.search(passage):
            rep.err(f"{title} · Passage {i+1}: contains placeholder text")

        questions = section.get("questions", [])
        if len(questions) != QCOUNTS[i]:
            rep.err(f"{title} · Passage {i+1}: {len(questions)} questions (expected {QCOUNTS[i]})")
        total_q += len(questions)
        orders = [q.get("order") for q in questions]
        if len(orders) != len(set(orders)):
            rep.err(f"{title} · Passage {i+1}: duplicate question order")

        norm_passage = _norm(passage)
        for q in questions:
            rep.questions += 1
            qid = f"{title} · Q{q.get('order', '?')}"
            qtype = q.get("question_type")
            if qtype not in QUESTION_TYPES:
                rep.err(f"{qid}: unknown question_type '{qtype}'")
            answers = q.get("correct_answer")
            if not answers or not isinstance(answers, list):
                rep.err(f"{qid}: missing/invalid correct_answer")
                answers = []
            allowed_answers = POLARITY_ANSWERS.get(qtype)
            if allowed_answers:
                normalized_answers = {str(answer).strip().lower() for answer in answers}
                normalized_options = {str(option).strip().lower() for option in (q.get("options") or [])}
                if not normalized_answers <= allowed_answers:
                    rep.err(f"{qid}: answers do not match {qtype}")
                if normalized_options and normalized_options != allowed_answers:
                    rep.err(f"{qid}: options do not match {qtype}")
            if not q.get("explanation"):
                rep.err(f"{qid}: missing explanation")

            is_ng = any(str(a).strip().lower() in NOT_GIVEN for a in answers)
            ev = q.get("evidence")
            spans = ev if isinstance(ev, list) else ([ev] if ev else [])
            if not spans:
                if not is_ng:
                    rep.err(f"{qid}: missing evidence")
                continue
            for s in spans:
                if s.get("paragraph") is None:
                    rep.err(f"{qid}: evidence missing paragraph")
                if s.get("sentence") is None:
                    rep.err(f"{qid}: evidence missing sentence")
                quote = s.get("quote", s.get("text"))
                if not quote:
                    rep.err(f"{qid}: evidence missing quote")
                    continue
                if _norm(quote) not in norm_passage:
                    rep.err(f"{qid}: evidence quote not found verbatim: \"{quote[:60]}…\"")

    if total_q != 40:
        rep.err(f"{title}: {total_q} questions total (expected 40)")
    lo, hi = TOTAL_WORD_RANGE
    rep.t_words.append(total_words)
    if not (lo <= total_words <= hi):
        rep.err(f"{title}: {total_words} passage words total (official IELTS Academic range {lo}-{hi})")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate Academic Reading content packs.")
    parser.add_argument(
        "--files", nargs="+", metavar="PATH",
        help="Validate only these JSON files (per-test rules only; skips the "
             "full-pack count check). Use for batch authoring.",
    )
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="Scan the whole content/reading directory but skip the "
             f"exactly-{EXPECTED_TESTS}-tests rule (per-test rules still enforced).",
    )
    args = parser.parse_args()

    rep = Report()
    partial = bool(args.files) or args.allow_partial

    if args.files:
        files = [Path(f) for f in args.files]
    else:
        if not CONTENT_DIR.exists():
            print(f"No content directory: {CONTENT_DIR}")
            return 1
        files = sorted(CONTENT_DIR.glob("*.json"))

    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            rep.err(f"{path.name}: cannot read ({e})")
            continue
        for t in raw.get("tests", []):
            validate_test(t, path.name, rep)

    # The full-pack rule (exactly EXPECTED_TESTS) is only enforced in a full scan,
    # never weakened — batch/partial modes simply defer it.
    if not partial and rep.tests != EXPECTED_TESTS:
        rep.err(f"expected {EXPECTED_TESTS} reading tests, found {rep.tests}")

    print(f"Reading content validation{' (partial)' if partial else ''}")
    print(f"  files scanned : {len(files)}")
    print(f"  reading tests : {rep.tests}" + ("" if partial else f" (target {EXPECTED_TESTS})"))
    print(f"  questions     : {rep.questions}")
    if rep.p_words:
        print(f"  passage words : min {min(rep.p_words)}, max {max(rep.p_words)}")
    if rep.t_words:
        print(f"  test words    : min {min(rep.t_words)}, max {max(rep.t_words)}")
    if rep.errors:
        print(f"\n  {len(rep.errors)} issue(s):")
        for e in rep.errors:
            print(f"   ✗ {e}")
        return 1
    print("\n  ✓ all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
