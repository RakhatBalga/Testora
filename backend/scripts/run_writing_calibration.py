#!/usr/bin/env python
"""Run live Gemini Writing calibration samples.

This is intentionally outside pytest: it calls the paid model, is non-
deterministic, and often uses private or third-party reference essays.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.config import settings  # noqa: E402
from app.infrastructure.ai.gemini import GeminiWritingGrader  # noqa: E402


@dataclass(frozen=True)
class Sample:
    id: str
    task_type: int
    prompt: str
    text: str
    expected_band: float | None = None
    expected_min: float | None = None
    expected_max: float | None = None
    min_words: int | None = None
    source: str | None = None
    notes: str | None = None


@dataclass
class Result:
    id: str
    task_type: int
    expected_band: float | None
    expected_min: float | None
    expected_max: float | None
    actual_band: float
    criteria: dict[str, float]
    passed: bool
    error: bool
    latency_seconds: float
    summary: str
    notes: str | None = None


def _read_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        if "samples" in data and isinstance(data["samples"], list):
            return data["samples"]
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError(f"{path} must contain a JSON object, a samples array, or a list")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no} is not valid JSONL: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no} must be a JSON object")
        rows.append(row)
    return rows


def load_samples(path: Path) -> list[Sample]:
    rows = _read_jsonl(path) if path.suffix == ".jsonl" else _read_json(path)
    samples: list[Sample] = []
    for index, row in enumerate(rows, 1):
        try:
            task_type = int(row["task_type"])
            sample = Sample(
                id=str(row.get("id") or f"sample_{index:03d}"),
                task_type=task_type,
                prompt=str(row["prompt"]).strip(),
                text=str(row["text"]).strip(),
                expected_band=(
                    float(row["expected_band"])
                    if row.get("expected_band") is not None
                    else None
                ),
                expected_min=(
                    float(row["expected_min"])
                    if row.get("expected_min") is not None
                    else None
                ),
                expected_max=(
                    float(row["expected_max"])
                    if row.get("expected_max") is not None
                    else None
                ),
                min_words=(
                    int(row["min_words"]) if row.get("min_words") is not None else None
                ),
                source=str(row["source"]) if row.get("source") else None,
                notes=str(row["notes"]) if row.get("notes") else None,
            )
        except KeyError as exc:
            raise ValueError(f"sample {index} is missing required field {exc}") from exc
        if sample.task_type not in {1, 2}:
            raise ValueError(f"{sample.id}: task_type must be 1 or 2")
        if not sample.prompt:
            raise ValueError(f"{sample.id}: prompt is required")
        if not sample.text:
            raise ValueError(f"{sample.id}: text is required")
        samples.append(sample)
    return samples


def expected_window(sample: Sample, tolerance: float) -> tuple[float | None, float | None]:
    low = sample.expected_min
    high = sample.expected_max
    if sample.expected_band is not None:
        low = sample.expected_band - tolerance if low is None else low
        high = sample.expected_band + tolerance if high is None else high
    return low, high


def run_sample(sample: Sample, tolerance: float) -> Result:
    min_words = sample.min_words if sample.min_words is not None else (150 if sample.task_type == 1 else 250)
    start = time.perf_counter()
    feedback = GeminiWritingGrader().grade(
        task_type=sample.task_type,
        prompt=sample.prompt,
        text=sample.text,
        min_words=min_words,
    )
    elapsed = round(time.perf_counter() - start, 2)
    low, high = expected_window(sample, tolerance)
    passed = not feedback.error
    if low is not None:
        passed = passed and feedback.band >= low
    if high is not None:
        passed = passed and feedback.band <= high
    return Result(
        id=sample.id,
        task_type=sample.task_type,
        expected_band=sample.expected_band,
        expected_min=low,
        expected_max=high,
        actual_band=feedback.band,
        criteria=feedback.criteria,
        passed=passed,
        error=feedback.error,
        latency_seconds=elapsed,
        summary=feedback.summary,
        notes=sample.notes,
    )


def print_result(result: Result) -> None:
    window = ""
    if result.expected_min is not None or result.expected_max is not None:
        low = "*" if result.expected_min is None else result.expected_min
        high = "*" if result.expected_max is None else result.expected_max
        window = f" expected={low}-{high}"
    marker = "PASS" if result.passed else "FAIL"
    print(
        f"{marker} {result.id}: band={result.actual_band:.1f}{window} "
        f"latency={result.latency_seconds:.2f}s"
    )
    if result.criteria:
        criteria = ", ".join(f"{k}={v:.1f}" for k, v in result.criteria.items())
        print(f"  criteria: {criteria}")
    if result.error:
        print(f"  error: {result.summary}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live Gemini IELTS Writing calibration samples."
    )
    parser.add_argument("samples", type=Path, help="JSON or JSONL calibration file")
    parser.add_argument("--model", help="Override GEMINI_MODEL for this run")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.5,
        help="Band tolerance around expected_band (default: 0.5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only run the first N samples (default: all)",
    )
    parser.add_argument(
        "--coach",
        action="store_true",
        help="Enable second-stage coaching call; disabled by default to save cost",
    )
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.model:
        settings.GEMINI_MODEL = args.model
    settings.WRITING_COACH_ENABLED = bool(args.coach)

    if settings.AI_PROVIDER.lower() != "gemini" or not settings.GEMINI_API_KEY:
        print(
            "AI_PROVIDER=gemini and GEMINI_API_KEY are required in backend/.env",
            file=sys.stderr,
        )
        return 2

    samples = load_samples(args.samples)
    if args.limit:
        samples = samples[: args.limit]
    if not samples:
        print("No calibration samples found.", file=sys.stderr)
        return 2

    print(
        f"Running {len(samples)} Writing calibration sample(s) with "
        f"model={settings.GEMINI_MODEL}, coach={settings.WRITING_COACH_ENABLED}"
    )

    results: list[Result] = []
    for sample in samples:
        result = run_sample(sample, args.tolerance)
        results.append(result)
        print_result(result)

    exact_errors = [
        abs(r.actual_band - r.expected_band)
        for r in results
        if r.expected_band is not None and not r.error
    ]
    failed = [r for r in results if not r.passed]
    summary = {
        "model": settings.GEMINI_MODEL,
        "coach_enabled": settings.WRITING_COACH_ENABLED,
        "sample_count": len(results),
        "pass_count": len(results) - len(failed),
        "fail_count": len(failed),
        "mean_absolute_error": round(mean(exact_errors), 3) if exact_errors else None,
        "results": [asdict(r) for r in results],
    }
    print(
        f"Summary: {summary['pass_count']}/{summary['sample_count']} passed; "
        f"MAE={summary['mean_absolute_error']}"
    )

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        print(f"Report written to {args.report}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
