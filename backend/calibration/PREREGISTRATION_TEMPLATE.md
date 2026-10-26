# E1 (Writing accuracy) pre-registration

Fill this in and freeze it BEFORE any test or gold essay is graded. Generate the
machine-readable block from real files with:

    python -m ml.evaluate_writing --dataset essays.jsonl --manifest manifest.json \
        --split test --cache <dev/pilot cache> --primary "<system name>" \
        --write-prereg calibration/prereg-e1.md

Then commit the file (or tag the commit) and record its sha256. `ml.evaluate_writing`
refuses to score `test` or `gold` without it and lists every deviation in the report.

## Frozen items

- Prompt version (sha256 of prompts.py + schemas.py, 12 chars): see block
- Model(s) and provider(s), including Qwen quantisation / server build: see block
- Temperature, seed policy, runs per essay (primary prediction = run 0): ______
- Datasets, licences, split fingerprints (from the split manifest): see block
- Test set is touched once. No prompt, threshold or model change after seeing it.

## Hypotheses and thresholds (docs/09, E1)

- Primary system: see block (`primary_system`)
- QWK (overall, half-band bins) >= 0.60, and the lower 95% bootstrap bound reported
- MAE <= 0.50; within +-0.5 band >= 70%
- Coverage of the primary system >= 95% of the split (failures count against it)
- Compared against: constant mean, constant mode, rule-based mock, Ridge, GBM
- Human-human QWK/MAE on the gold set is the ceiling row

## Analysis plan

- Metrics: QWK, MAE, RMSE, bias, exact / +-0.5 / +-1.0 agreement, Pearson, Spearman,
  SD of predictions vs labels, share of the modal prediction, confusion matrix
- 95% percentile bootstrap, 2000 resamples; paired bootstrap for system differences
- Failures are reported as coverage; metrics use essays covered by all systems
- Stability: 5 runs on the gold set; SD, ICC(2,1), pairwise QWK
- Negative results are reported as such

## Frozen block (do not edit by hand)

<<FROZEN_BLOCK>>
