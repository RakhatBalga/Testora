#!/usr/bin/env python
"""Back-compat wrapper for the old calibration runner.

The runner moved to the E1 tooling in ml/ (offline evaluator, caching, repeated
runs, baselines, bootstrap CIs). This script keeps the old entry point: it
converts a legacy calibration JSONL into the `writing-essay.v1` dev split, grades
it with the chosen provider and prints the evaluation. See calibration/README.md
("How to run E1") for the full workflow.
"""
import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml import collect_writing, evaluate_writing  # noqa: E402
from ml.writing_data import load_calibration_bank, write_essays  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path, help="legacy calibration JSONL")
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--cache", type=Path, default=Path("calibration/reports/dev-cache.jsonl"))
    parser.add_argument("--report", type=Path, help="output prefix for <prefix>.md / .json")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        dataset = Path(tmp) / "dev.jsonl"
        write_essays(dataset, load_calibration_bank(args.samples))
        base = ["--dataset", str(dataset), "--split", "dev", "--cache", str(args.cache)]
        collect = ["--provider", args.provider, "--runs", str(args.runs)]
        if args.model:
            collect += ["--model", args.model]
        if args.limit:
            collect += ["--limit", str(args.limit)]
        code = collect_writing.main(base[:4] + collect + base[4:])
        evaluate = base + ["--run-mock", "--mock-cache", str(args.cache.with_name("mock-cache.jsonl")),
                           "--n-boot", "500"]
        if args.report:
            evaluate += ["--out", str(args.report)]
        evaluate_writing.main(evaluate)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
