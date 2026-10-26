"""E1 collector: run one grader over a split and cache every raw response.

    python -m ml.collect_writing --dataset essays.jsonl --split test \\
        --provider gemini --runs 5 --cache ml/data/e1-cache.jsonl --rps 0.5

The cache is append-only JSONL; the last record for a key wins. A key is
(essay text hash, provider, model, prompt_version, seed, run). Successes are never
re-requested (resume); failures are stored explicitly (ok=false + reason), retried
on the next invocation unless --no-retry-failed, and always counted in the
coverage that evaluate_writing reports. The cache holds essay hashes, not essay
text, but raw model output can quote essays: keep it out of Git (ml/data/ is ignored).
"""

import argparse
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ml import graders
from ml.writing_data import Essay, canonical_criteria, read_essays

CACHE_VERSION = "writing-cache.v1"
KEY_FIELDS = ("essay_hash", "provider", "model", "prompt_version", "seed", "run")


def min_words_for(task_type: int) -> int:
    return 150 if task_type == 1 else 250


def cache_key(essay_hash, provider, model, prompt_version, seed, run) -> str:
    return json.dumps([essay_hash, provider, model, prompt_version, seed, run])


def record_key(rec: dict) -> str:
    return cache_key(*(rec[f] for f in KEY_FIELDS))


def load_cache(path: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    path = Path(path)
    if not path.exists():
        return records
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            records[record_key(rec)] = rec
        except (ValueError, KeyError):
            raise ValueError(f"{path}:{number} is not a valid cache record") from None
    return records


@dataclass
class CollectSummary:
    requested: int = 0
    cached_ok: int = 0
    new_ok: int = 0
    failed: int = 0
    aborted: bool = False
    failure_reasons: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "requested": self.requested,
            "cached_ok": self.cached_ok,
            "new_ok": self.new_ok,
            "failed": self.failed,
            "aborted": self.aborted,
            "failure_reasons": self.failure_reasons,
        }


def _flags(feedback) -> dict | None:
    flags = getattr(feedback, "flags", None)
    return dict(flags) if isinstance(flags, dict) and flags else None


def collect(
    essays: list[Essay],
    grader,
    *,
    provider: str,
    model: str,
    prompt_version: str,
    cache_path: Path,
    runs: int = 1,
    seed: int = 0,
    rps: float = 0.0,
    retry_failed: bool = True,
    abort_after: int = 20,
    sleep=time.sleep,
    clock=time.monotonic,
    progress=None,
) -> CollectSummary:
    """Grade every essay `runs` times. Run order is run-major so a partial pass
    still has complete first runs (the primary prediction)."""
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = load_cache(cache_path)
    summary = CollectSummary()
    interval = 1.0 / rps if rps and rps > 0 else 0.0
    last_call = None
    streak = 0
    with cache_path.open("a", encoding="utf-8") as out:
        for run in range(runs):
            for essay in essays:
                summary.requested += 1
                key = cache_key(essay.text_hash, provider, model, prompt_version, seed, run)
                old = cache.get(key)
                if old is not None and (old["ok"] or not retry_failed):
                    summary.cached_ok += bool(old["ok"])
                    summary.failed += not old["ok"]
                    if not old["ok"]:
                        _count(summary, old.get("error"))
                    continue
                if interval and last_call is not None:
                    wait = interval - (clock() - last_call)
                    if wait > 0:
                        sleep(wait)
                last_call = clock()
                rec = _grade_once(grader, essay, provider, model, prompt_version, seed, run, clock)
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                cache[key] = rec
                if rec["ok"]:
                    summary.new_ok += 1
                    streak = 0
                else:
                    summary.failed += 1
                    _count(summary, rec["error"])
                    streak += 1
                if progress:
                    progress(summary, essay, run, rec)
                if abort_after and streak >= abort_after:
                    summary.aborted = True
                    return summary
    return summary


def _count(summary: CollectSummary, reason) -> None:
    reason = str(reason or "unknown")[:80]
    summary.failure_reasons[reason] = summary.failure_reasons.get(reason, 0) + 1


def _grade_once(grader, essay, provider, model, prompt_version, seed, run, clock) -> dict:
    base = {
        "cache_version": CACHE_VERSION,
        "essay_hash": essay.text_hash,
        "essay_id": essay.id,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "seed": seed,
        "run": run,
        "task_type": essay.task_type,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    started = clock()
    try:
        fb = graders.grade_call(
            grader,
            task_type=essay.task_type,
            prompt=essay.prompt,
            text=essay.text,
            min_words=min_words_for(essay.task_type),
            seed=seed,
        )
    except Exception as exc:  # any provider failure is data, not a crash
        return {
            **base,
            "ok": False,
            "error": f"{type(exc).__name__}: {str(exc)[:120]}",
            "latency": round(clock() - started, 3),
            "band": None,
            "criteria": {},
            "flags": None,
            "raw": None,
        }
    latency = round(clock() - started, 3)
    if getattr(fb, "error", False):
        return {
            **base,
            "ok": False,
            "error": f"grader error: {str(getattr(fb, 'summary', ''))[:100]}",
            "latency": latency,
            "band": None,
            "criteria": {},
            "flags": None,
            "raw": None,
        }
    return {
        **base,
        "ok": True,
        "error": None,
        "latency": latency,
        "band": float(fb.band),
        "criteria": canonical_criteria(fb.criteria),
        "flags": _flags(fb),
        "raw": fb.to_dict() if hasattr(fb, "to_dict") else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", required=True, choices=["dev", "train", "test", "gold", "all"])
    parser.add_argument("--provider", required=True, help="mock | gemini | claude | qwen")
    parser.add_argument("--model", help="model id to record (default: from settings)")
    parser.add_argument("--prompt-version", help="override the auto prompt hash")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rps", type=float, default=0.0, help="max requests per second (0 = unlimited)")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-retry-failed", action="store_true")
    parser.add_argument("--abort-after", type=int, default=20, help="stop after N consecutive failures")
    args = parser.parse_args(argv)

    essays = [e for e in read_essays(args.dataset) if args.split == "all" or e.split == args.split]
    if args.limit:
        essays = essays[: args.limit]
    if not essays:
        raise SystemExit("no essays in that split")
    grader = graders.make_grader(args.provider)
    model = args.model or graders.model_name(args.provider, grader)
    version = graders.prompt_version(args.prompt_version)
    print(
        f"collecting {len(essays)} essays x {args.runs} runs: provider={args.provider} "
        f"model={model} prompt_version={version} seed={args.seed}"
    )
    summary = collect(
        essays,
        grader,
        provider=args.provider,
        model=model,
        prompt_version=version,
        cache_path=args.cache,
        runs=args.runs,
        seed=args.seed,
        rps=args.rps,
        retry_failed=not args.no_retry_failed,
        abort_after=args.abort_after,
        progress=lambda s, e, run, rec: print(
            f"  run {run} {e.id}: {'ok band=%s' % rec['band'] if rec['ok'] else 'FAILED ' + rec['error']}"
        ),
    )
    print(json.dumps(summary.as_dict(), indent=2))
    return 1 if summary.aborted or summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
