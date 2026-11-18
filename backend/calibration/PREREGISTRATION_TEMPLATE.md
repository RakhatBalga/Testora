# E1 (Writing accuracy) pre-registration

Fill this in and freeze it BEFORE any test or gold essay is graded. Generate the
machine-readable block from real files with:

    python -m ml.evaluate_writing --dataset essays.jsonl --manifest manifest.json \
        --split test --cache <dev/pilot cache> --primary "<system name>" \
        --write-prereg calibration/prereg-e1.md

Then commit the file (or tag the commit) and record its sha256. `ml.evaluate_writing`
refuses to score `test` or `gold` without it and lists every deviation in the report.

## Frozen items

- Examiner prompt version (`v1` or `v2`) and its cache key
  (`examiner-<v>+<prompt fingerprint>+src.<hash of prompts.py + schemas.py>`): see block
- Model(s) and provider(s), including Qwen quantisation / server build: see block
- Seed: the effective value recorded by the collector (see block; `null` = none sent)
- Temperature, runs per essay (primary prediction = run 0): ______
- Datasets, licences, split fingerprints (from the split manifest): see block
- Test set is touched once. No prompt, threshold or model change after seeing it.

## Hypotheses and thresholds (docs/09, E1)

- Primary system: see block (`primary_system`)
- QWK (overall, half-band bins) >= 0.60, and its lower 95% bootstrap bound >= 0.60
  (`qwk_ci_lower_min`)
- QWK >= 0.50 on each of the four criteria
- MAE <= 0.50; within +-0.5 band >= 70%
- Coverage of the primary system >= 95% of the split (failures count against it)
- Run-to-run stability: mean within-essay SD of the overall band over >= 5 runs <= 0.25
- Cap-case hit rate >= 90% of the essays labelled with `expected_caps`
- Lower MAE and higher QWK than every baseline: constant mean, constant mode,
  rule-based mock, Ridge, GBM
- A check whose inputs are missing is reported as not evaluable; the result is then
  incomplete, not passed
- Rater 2 vs rater 1 QWK/MAE on the gold set is reported as the level of human
  agreement. It is scored against the other rater, not against the final label, so it
  is not like-for-like with the system rows

## Analysis plan

- Metrics: QWK, MAE, RMSE, bias, exact / +-0.5 / +-1.0 agreement, Pearson, Spearman,
  SD of predictions vs labels, share of the modal prediction, confusion matrix
- 95% percentile bootstrap, 2000 resamples; paired bootstrap for system differences
- Failures are reported as coverage; metrics use essays covered by all systems
- Stability: 5 runs on the gold set; SD, ICC(2,1), pairwise QWK
- Negative results are reported as such

## Frozen block (do not edit by hand)

<<FROZEN_BLOCK>>
