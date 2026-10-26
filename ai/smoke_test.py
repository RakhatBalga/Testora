#!/usr/bin/env python
"""Smoke test for a Qwen server: one real Writing grading through the backend.

Uses the production pipeline (shared prompts, schema, normalisation), not a
toy request, so a pass means AI_PROVIDER=qwen will work with this server.

    cd backend
    QWEN_BASE_URL=http://localhost:11434/v1 QWEN_MODEL=testora-qwen3 \
        venv/bin/python ../ai/smoke_test.py

Exit code 0 = graded, 1 = server unreachable / model missing / grading failed.
Never point this at a paid provider; it only talks to QWEN_BASE_URL.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
# Settings require these at import; the smoke test never touches a database.
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@localhost:5432/unused")
os.environ.setdefault("SECRET_KEY", "smoke-test-only")

from app.infrastructure.ai.qwen import QwenWritingGrader, ping_qwen  # noqa: E402
from app.infrastructure.config import settings  # noqa: E402

TASK = (
    "Some people think that governments should spend money on public transport "
    "rather than on building new roads. To what extent do you agree or disagree?"
)
ESSAY = """Traffic congestion is one of the most visible problems in modern cities, and governments must decide how to spend limited transport budgets. I largely agree that public transport deserves more funding than new roads, although some road investment remains necessary.

The main reason is efficiency. A single bus or train carries dozens or hundreds of passengers while using far less space than the same number of private cars. When a city such as Almaty builds another highway, the extra lanes usually fill up within a few years, because cheaper driving encourages more people to drive. By contrast, a reliable metro line can move large numbers of commuters without making traffic worse.

Public transport also has social and environmental benefits. Not everyone can afford a car, so cheap and frequent buses give students, older people and low-income workers access to jobs and education. In addition, fewer cars on the road means less air pollution, which is a serious health issue in many growing cities.

However, roads cannot be ignored completely. Rural areas often have too few passengers to justify trains, and goods are still delivered by lorries. Therefore, governments should maintain existing roads and build new ones where there is no realistic alternative.

In conclusion, I believe most new transport spending should go to public transport, because it moves more people, is fairer and is better for the environment, while road building should be limited to places where it is genuinely needed."""


def main() -> int:
    if not (settings.QWEN_BASE_URL and settings.QWEN_MODEL):
        print("Set QWEN_BASE_URL and QWEN_MODEL first (see docs/qwen.md).")
        return 1
    print(f"Server: {settings.QWEN_BASE_URL}  model: {settings.QWEN_MODEL}")
    health = asyncio.run(ping_qwen())
    print("GET /models:", json.dumps(health))
    if not health["ok"]:
        return 1
    if not health["model_available"]:
        print("warning: model id not listed by the server; check QWEN_MODEL spelling.")

    started = time.monotonic()
    fb = QwenWritingGrader().grade(task_type=2, prompt=TASK, text=ESSAY, min_words=250)
    elapsed = time.monotonic() - started
    print(f"\nLatency: {elapsed:.1f} s (examiner{' + coach' if settings.WRITING_COACH_ENABLED else ''})")
    print("Result:", json.dumps({
        "band": fb.band,
        "criteria": fb.criteria,
        "summary": fb.summary,
        "mistakes": len(fb.mistakes),
        **fb.diagnostics(),
    }, indent=2, ensure_ascii=False))
    return 1 if fb.error else 0


if __name__ == "__main__":
    raise SystemExit(main())
