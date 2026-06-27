"""Validate structured IELTS Academic Writing Task 1 content."""
from __future__ import annotations

import json
import sys
from pathlib import Path


CONTENT_DIR = Path(__file__).resolve().parent / "content" / "writing"
KINDS = {"line", "bar", "table", "pie", "process", "map"}


def validate_task(task: dict, where: str) -> list[str]:
    errors: list[str] = []
    title = task.get("title", where)
    if task.get("task_type") != 1:
        return errors
    if task.get("min_words") != 150:
        errors.append(f"{title}: Task 1 min_words must be 150")
    if task.get("duration_minutes") != 20:
        errors.append(f"{title}: Task 1 duration must be 20 minutes")
    if not task.get("prompt"):
        errors.append(f"{title}: missing prompt")

    visual = task.get("visual_data")
    if not isinstance(visual, dict):
        errors.append(f"{title}: missing visual_data")
        return errors
    kind = visual.get("kind")
    if kind not in KINDS:
        errors.append(f"{title}: unknown visual kind '{kind}'")
    elif kind in {"line", "bar"}:
        categories = visual.get("categories")
        series = visual.get("series")
        if not categories or not series:
            errors.append(f"{title}: chart requires categories and series")
        elif any(len(item.get("values", [])) != len(categories) for item in series):
            errors.append(f"{title}: every series must match category count")
    elif kind == "table" and (not visual.get("columns") or not visual.get("rows")):
        errors.append(f"{title}: table requires columns and rows")
    elif kind == "pie" and len(visual.get("charts", [])) < 2:
        errors.append(f"{title}: pie comparison requires at least two charts")
    elif kind == "process" and len(visual.get("steps", [])) < 3:
        errors.append(f"{title}: process requires at least three steps")
    elif kind == "map" and (not visual.get("before") or not visual.get("after")):
        errors.append(f"{title}: map requires before and after features")
    return errors


def main() -> int:
    errors: list[str] = []
    tasks = 0
    kinds: set[str] = set()
    files = sorted(CONTENT_DIR.glob("*.json"))
    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{path.name}: cannot read ({exc})")
            continue
        for task in raw.get("writing_tasks", []):
            if task.get("task_type") != 1:
                continue
            tasks += 1
            visual = task.get("visual_data") or {}
            if visual.get("kind"):
                kinds.add(visual["kind"])
            errors.extend(validate_task(task, path.name))

    if tasks < 6:
        errors.append(f"expected at least 6 Task 1 prompts, found {tasks}")
    missing = KINDS - kinds
    if missing:
        errors.append(f"missing Task 1 visual kinds: {', '.join(sorted(missing))}")

    print("Writing Task 1 content validation")
    print(f"  files scanned : {len(files)}")
    print(f"  Task 1 prompts: {tasks}")
    print(f"  visual kinds  : {', '.join(sorted(kinds)) or 'none'}")
    if errors:
        print(f"\n  {len(errors)} issue(s):")
        for error in errors:
            print(f"   x {error}")
        return 1
    print("\n  all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
