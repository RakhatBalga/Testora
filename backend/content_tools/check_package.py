"""Offline Reading/Listening release check; never imports application or DB code.

Run: python -m content_tools.check_package content/reading/example.json
Exit 0 means structural checks passed, not editorial approval or DB import.
"""

import argparse
import json
from pathlib import Path

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


def check_package(data, asset_root: Path) -> list[str]:
    errors = []

    def require(ok, where, message):
        if not ok:
            errors.append(f"{where}: {message}")

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def positive(value):
        return type(value) is int and value > 0

    if not isinstance(data, dict) or not isinstance(data.get("tests"), list) or not data["tests"]:
        return ["package: tests must be a non-empty array"]
    require(not (set(data) - {"tests"}), "package", "only Reading/Listening tests are supported")
    keys = set()
    for ti, test in enumerate(data["tests"], 1):
        where = f"test {ti}"
        if not isinstance(test, dict):
            errors.append(f"{where}: must be an object")
            continue
        skill = test.get("test_type")
        require(skill in ("reading", "listening"), where, "invalid test_type")
        require(text(test.get("title")), where, "title is required")
        key = (str(skill), str(test.get("title")))
        require(key not in keys, where, "duplicate test natural key")
        keys.add(key)
        require(
            text(test.get("content_version")) and test.get("content_version") != "legacy",
            where,
            "explicit content_version required",
        )
        require(positive(test.get("duration_minutes")), where, "duration_minutes must be a positive integer")
        meta = test.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        require(type(meta.get("published")) is bool, where, "published must be an explicit boolean")
        require(
            not (meta.get("published") is True and meta.get("superseded_by")),
            where,
            "superseded content cannot be published",
        )
        if meta.get("published") is True:
            rights = meta.get("rights", {})
            require(
                isinstance(rights, dict) and rights.get("publication_allowed") is True and text(rights.get("evidence")),
                where,
                "publication requires rights.publication_allowed=true and rights.evidence",
            )
        sections = test.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append(f"{where}: sections must be a non-empty array")
            continue
        section_orders, question_orders = set(), set()
        for si, section in enumerate(sections, 1):
            sw = f"{where}/section {si}"
            if not isinstance(section, dict):
                errors.append(f"{sw}: must be an object")
                continue
            order = section.get("order", si)
            require(
                positive(order) and order not in section_orders,
                sw,
                "invalid or duplicate order",
            )
            if positive(order):
                section_orders.add(order)
            require(text(section.get("title")), sw, "title is required")
            if skill == "reading":
                require(text(section.get("passage")), sw, "passage is required")
            if skill == "listening":
                url = section.get("audio_url")
                if not isinstance(url, str) or not url.startswith("/static/audio/"):
                    errors.append(
                        f"{sw}: audio must use a local /static/audio/ asset; remote audio verification unsupported"
                    )
                else:
                    path = (asset_root / url.lstrip("/")).resolve()
                    require(
                        path.is_relative_to((asset_root / "static/audio").resolve()) and path.is_file(),
                        sw,
                        "audio missing or outside static/audio",
                    )
            questions = section.get("questions")
            if not isinstance(questions, list) or not questions:
                errors.append(f"{sw}: questions must be a non-empty array")
                continue
            for qi, q in enumerate(questions, 1):
                qw = f"{sw}/question {qi}"
                if not isinstance(q, dict):
                    errors.append(f"{qw}: must be an object")
                    continue
                order = q.get("order", qi)
                require(
                    type(order) is int and order > 0 and order not in question_orders,
                    qw,
                    "question order must be positive and unique across test",
                )
                if positive(order):
                    question_orders.add(order)
                require(text(q.get("text")), qw, "text is required")
                kind = q.get("question_type")
                require(isinstance(kind, str) and kind in QUESTION_TYPES, qw, "unsupported question_type")
                answers = q.get("correct_answer")
                require(
                    isinstance(answers, list) and bool(answers) and all(text(a) for a in answers),
                    qw,
                    "non-empty string answer list required",
                )
                options = q.get("options")
                if options is not None:
                    require(
                        isinstance(options, list) and bool(options) and all(text(o) for o in options),
                        qw,
                        "options must be a non-empty string list",
                    )
                if kind in ("single_choice", "multiple_choice"):
                    require(
                        isinstance(options, list) and len(options) >= 2,
                        qw,
                        "choice questions require at least two options",
                    )
                    if isinstance(options, list) and all(text(o) for o in options) and isinstance(answers, list):
                        allowed = {o.strip().casefold() for o in options}
                        allowed.update(chr(97 + i) for i in range(min(len(options), 26)))
                        require(
                            all(text(a) and a.strip().casefold() in allowed for a in answers),
                            qw,
                            "choice answer must match an option or its letter",
                        )
                        require(
                            kind != "single_choice" or len(answers) == 1,
                            qw,
                            "single_choice requires exactly one answer",
                        )
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--asset-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    reports = []
    for file in args.files:
        try:
            errors = check_package(json.loads(file.read_text(encoding="utf-8-sig")), args.asset_root)
        except (OSError, ValueError):
            errors = ["Cannot read a valid UTF-8 JSON package"]
        reports.append({"file": str(file), "errors": errors, "valid": not errors})
    print(
        json.dumps(
            {
                "database_access": False,
                "scope": "structure, publication metadata, local audio presence; not editorial/media validation",
                "packages": reports,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(any(not r["valid"] for r in reports))


if __name__ == "__main__":
    raise SystemExit(main())
