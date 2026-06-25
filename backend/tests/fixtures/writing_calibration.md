# Writing calibration fixtures (live-Gemini validation)

These labelled essays validate end-to-end grading accuracy against the *real*
model — they cannot run in CI (cost + non-determinism). Run manually with
`AI_PROVIDER=gemini` and a key set, then compare the engine's overall band to the
expected band (±0.5 is the target tolerance; trained human examiners themselves
agree within ~0.5).

How to run (per essay): POST to `/writing/submit` (or call
`GeminiWritingGrader().grade(...)` directly) and record overall + criteria.

Expected bands are reference labels; the engine should land within ±0.5 and must
apply the hard caps (no overview / fabrication / off-topic / under-length).

## Task 2

| id | expected overall | what it exercises |
|----|------------------|-------------------|
| t2_band4 | 4.0 | minimal development, frequent impeding errors |
| t2_band5 | 5.0 | partial answer, repetitive vocab, limited range |
| t2_band6 | 6.0 | addresses task, some thin support, mixed accuracy |
| t2_band7 | 7.0 | clear position, developed ideas, good cohesion |
| t2_band8 | 8.0 | fully developed, wide precise language, rare slips |
| t2_offtopic | ≤4.0 | ignores the prompt — Task Response cap must fire |
| t2_underlength | ≤5.0 | ~150 words on a 250-word task — length cap must fire |

## Task 1 (Academic)

| id | expected overall | what it exercises |
|----|------------------|-------------------|
| t1_band4 | 4.0 | lists numbers, no structure |
| t1_band5 | 5.0 | describes detail but NO overview — TA cap at 5 |
| t1_band6 | 6.0 | overview present, some comparisons, mixed accuracy |
| t1_band7 | 7.0 | clear overview, well-selected key features + comparisons |
| t1_band8 | 8.0 | fully selective, accurate, well-organised |
| t1_fabricated | ≤4.0 | invents data/trends not in the chart — fabrication cap |
| t1_no_overview | ≤5.0 | strong detail, missing overview — TA cap at 5 |

Populate the essay bodies from a calibrated bank (e.g. official IELTS sample
answers with published examiner bands) before running. Track the mean absolute
error vs expected bands across the set; investigate any case off by > 0.5.
