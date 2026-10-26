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
WRITING_COACH_ENABLED=false venv/bin/python scripts/dev/run_writing_calibration.py \
  calibration/writing_samples.local.jsonl \
  --model gemini-2.5-flash \
  --tolerance 0.5 \
  --report calibration/reports/latest.json
```

The script prints every model score, flags samples outside the accepted band
range, and writes a JSON report when `--report` is provided.

## How to run E1 (Writing accuracy)

The old single-purpose runner (`scripts/dev/run_writing_calibration.py`) is now a thin
wrapper. E1 is a pipeline of four offline commands in `backend/ml/`; only step 3
calls a paid or remote model. Run everything from `backend/` with
`pip install -r requirements-dev.txt -r requirements-ml.txt`.
Outputs go to `ml/data/`, `ml/artifacts/`, `ml/reports/` (all git-ignored).

Dataset schema `writing-essay.v1` is documented in the docstring of
`ml/writing_data.py`. Splits: `dev` = the 8-essay bank (prompt was tuned on it,
never a test set), `train`/`test` = public corpus split by prompt group,
`gold` = double-marked teacher set.

**1. Build the dataset and split manifest** (dedup: exact + near-duplicate; gold >
public > bank priority)

```bash
python -m ml.writing_data \
  --bank tests/fixtures/writing_calibration_bank.jsonl \
  --public-csv ml/data/ielts_scored_essays.csv \
  --public-source "Kaggle IELTS Writing Scored Essays" --public-licence "<check the dataset page>" \
  --gold ml/data/gold.local.jsonl \
  --out ml/data/essays.jsonl --manifest ml/data/manifest.json
```

The public CSV is not downloaded by any script. Download it yourself, check its
licence, and verify the column names; the default mapping assumes
`Task_Type, Question, Essay, Overall, Task_Response, Coherence_Cohesion,
Lexical_Resource, Range_Accuracy`. Override with e.g. `--map prompt=Question
--map text=Essay`. Labels that are not half bands are snapped; rows without a
band/text/prompt are skipped and listed in the manifest. Public labels are
single, non-certified raters and the essays are probably in LLM training data:
call it a noisy-label benchmark with contamination risk.

Gold rows: `{"id","task_type","prompt","text","ratings":[{"rater_id":"T1","overall":6.5,
"criteria":{"task":6,"coherence":7,"lexical":6.5,"grammar":6.5}}, {...T2...}],
"adjudicated": {...}}`. Raters more than 1.0 apart need `adjudicated`. Student
essays must have written consent and must not go through a free-tier API.

Prompt leakage is blocked: public prompts that also occur in the dev bank or the
gold set are forced into `test`, never `train`, and `verify_manifest` reports any
prompt shared between train and test/gold/dev. The split is balanced greedily
toward `--test-fraction`; a warning is printed (and stored in the manifest) when a
dominant prompt makes the target unreachable by more than 10 points. Essays carry
recomputed `text_hash`/`prompt_id`; a stored hash that no longer matches the text
is an error, so an edited essay can never reuse a cached grade.

**2. Train the classical-ML baselines** (Ridge + gradient boosting, prompt-grouped CV)

```bash
python -m ml.train_writing --dataset ml/data/essays.jsonl --out-dir ml/artifacts/writing-v1
```

Refuses to overwrite an existing `--out-dir`. Writes `writing_models.joblib` and
`training_report.json` (CV metrics, out-of-fold predictions, metadata).

**3. Collect LLM responses** (resumable cache; failures are recorded and retried)

```bash
python -m ml.collect_writing --dataset ml/data/essays.jsonl --split test \
  --provider gemini --runs 1 --rps 0.5 --cache ml/data/e1-gemini.jsonl
python -m ml.collect_writing --dataset ml/data/essays.jsonl --split test \
  --provider qwen --runs 1 --cache ml/data/e1-qwen.jsonl
python -m ml.collect_writing --dataset ml/data/essays.jsonl --split gold \
  --provider gemini --runs 5 --cache ml/data/e1-gemini-gold.jsonl   # stability
```

Providers are resolved through `ml/graders.py` (`mock|gemini|claude|qwen`). It
refuses to run a provider that is not actually configured, instead of silently
grading with the mock. Use the dev split for the pilot and `--limit 3` for a
smoke test.

**4. Freeze the protocol, then evaluate once**

```bash
python -m ml.evaluate_writing --dataset ml/data/essays.jsonl --manifest ml/data/manifest.json \
  --split test --cache ml/data/e1-gemini.jsonl ml/data/e1-qwen.jsonl --primary "gemini:<model>" \
  --write-prereg calibration/prereg-e1.md          # fill in the template, commit/tag it

python -m ml.evaluate_writing --dataset ml/data/essays.jsonl --manifest ml/data/manifest.json \
  --split test --cache ml/data/e1-gemini.jsonl ml/data/e1-qwen.jsonl \
  --model-bundle ml/artifacts/writing-v1/writing_models.joblib --run-mock \
  --prereg calibration/prereg-e1.md --out ml/reports/e1-test
```

Bootstrap CIs resample whole prompts (cluster bootstrap) by default whenever
prompts repeat in the evaluated set, because essays on one prompt are not
independent; pass `--no-cluster-by-prompt` to resample essays instead.
Systems have a stable id (`provider|model|prompt_version|seed`); the pre-registered
primary system is matched by that id, a missing primary is an error, and the
verdict includes a coverage threshold (default >= 95% of the split). The
pre-registration also stores the dataset hash and the split fingerprints, which are
rechecked from the dataset itself (no manifest needed).

`test` and `gold` need `--prereg` (or an explicit `--allow-unregistered`, which is
printed in the report). Same command with `--split gold` adds the human-human
ceiling row. `--split train --oof ml/artifacts/writing-v1/training_report.json`
shows grouped-CV results for the trained models. The report
(`ml/reports/e1-test.md` / `.json`) has one row per system (constant mean/mode,
rules, Ridge, GBM, each LLM provider) with QWK, MAE, agreement, Pearson, bias,
prediction spread, mode share, coverage and 95% bootstrap CIs, plus per-criterion
results (`--ci-criteria` for their CIs), stability (ICC, SD, flips), paired
bootstrap differences and confusion matrices. Read QWK, SD ratio and mode share
together: a flat 7.0 predictor has QWK 0 but a respectable MAE.

Legacy shortcut for a quick dev-set check:
`python scripts/dev/run_writing_calibration.py tests/fixtures/writing_calibration_bank.jsonl --provider gemini`.
