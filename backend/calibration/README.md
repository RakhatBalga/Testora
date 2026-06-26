# Writing calibration

Use this folder for local-only Writing grader calibration data. Do not commit
third-party essays, student essays, API keys, or examiner material without clear
reuse rights.

Local sample files should use `.local.jsonl` or `.local.json` so git ignores
them. Each sample has this shape:

```json
{
  "id": "t2_high_band_01",
  "task_type": 2,
  "prompt": "Some people think...",
  "text": "Candidate essay...",
  "expected_band": 7.0,
  "expected_min": 6.5,
  "expected_max": 7.5,
  "source": "private calibration",
  "notes": "Optional rationale"
}
```

`expected_band` creates a default tolerance window. Use `expected_min` and
`expected_max` when the source only provides a range such as "Band 7-9".

Run from `backend/` with a Gemini key in `.env`:

```bash
WRITING_COACH_ENABLED=false venv/bin/python scripts/run_writing_calibration.py \
  calibration/writing_samples.local.jsonl \
  --model gemini-2.5-flash \
  --tolerance 0.5 \
  --report calibration/reports/latest.json
```

The script prints every model score, flags samples outside the accepted band
range, and writes a JSON report when `--report` is provided.
