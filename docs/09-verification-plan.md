# 9. Verification and Evaluation Plan

The project aim is to build an IELTS preparation system that (a) grades Writing (and later Speaking) close to expert examiners, (b) correctly identifies what keeps a learner's band from rising, and (c) helps learners improve. We demonstrate this at two levels:

1. **Verification:** the system does what Section 6 specifies. This is checked by automated tests in CI, content validators, and scripted security and end-to-end checks.
2. **Evaluation:** the system is good enough to be useful. This is checked by four experiments (E1–E4), each with a research question, data, metric, measurement conditions, a baseline, and a success threshold.

> **Honest status (22 October 2026):** no accuracy or pilot results exist yet. The measurement code is in place (`backend/scripts/run_writing_calibration.py`, `backend/ml/*`), but the labelled datasets are still being collected (YouTrack **TST-40**: Writing dataset, **TST-45**: Speaking dataset). All thresholds below are **targets**, not achieved results.

## 9.1 Testing plan

### 9.1.1 Existing automated tests

Counts are taken from the `main` branch: `def test_*` functions in the backend and `it(...)`/`test(...)` blocks in the frontend. Parametrised tests expand into more cases at run time.

**Backend – pytest: 34 files, 162 test functions** (`backend/tests/`)

| Area | Test files (number of test functions) |
|------|---------------------------------------|
| LLM Writing grading | `test_writing_examiner.py` (26), `test_gemini_grading.py` (14), `test_writing_precheck.py` (4), `test_writing_retry.py` (4) |
| Coach loop / analytics | `test_personalized_learning.py` (6), `test_recommendations.py` (2), `test_weekly_analytics.py` (1), `test_target_band.py` (8), `test_band.py` (6) |
| Reading / Listening | `test_reading_scoring.py` (4), `test_reading_catalog.py` (3), `test_listening_scoring.py` (6), `test_listening_updates.py` (4), `test_listening_validator.py` (4), `test_content_pipeline.py` (7) |
| Vocabulary | `test_vocabulary.py` (4), `test_vocabulary_quota.py` (3) |
| Security & reliability | `test_auth_tokens.py` (3), `test_google_auth.py` (5), `test_ratelimit.py` (2), `test_ai_safety.py` (7), `test_ai_quota.py` (6), `test_deploy_paths.py` (3) |
| ML research modules | `test_ml_asr.py` (1), `test_ml_benchmark_asr.py` (2), `test_ml_data.py` (3), `test_ml_speech_features.py` (3), `test_ml_train_speaking.py` (2), `test_ml_metrics.py` (3), `test_ml_irt.py` (2), `test_ml_knowledge_tracing.py` (3), `test_ml_recommendation.py` (2), `test_ml_evaluate_adaptive.py` (3), `test_ml_export_responses.py` (6) |

**Frontend – Vitest + Testing Library: 12 files, 40 test blocks (41 cases at run time)**

`features/auth/googleFlow.test.ts` (4), `features/auth/ui/GoogleSignInButton.test.tsx` (2), `app/login/page.test.tsx` (1), `shared/api/login.test.ts` (5), `shared/api/quotaErrors.test.ts` (2), `features/feedback/ui/ReviewStatusNotice.test.tsx` (2), `features/listening-session/progress.test.ts` (8), `app/listening/progress.test.tsx` (5), `features/listening-session/ui/ListeningAudioPlayer.test.tsx` (1 `it.each` → 2 cases), `shared/ui/Button.test.tsx` (3), `shared/lib/formatDisplayName.test.ts` (4), `shared/lib/greeting.test.ts` (3).

**Content validators** (run in CI before the tests):

| Validator | What it checks |
|-----------|----------------|
| `validate_reading.py` | Every question (except "Not Given") has evidence with paragraph, sentence and a quote found **verbatim** in the passage. Answer keys and question types are well-formed |
| `validate_listening.py` | Test structure, evidence quotes in transcripts, and the **real audio duration** (ffmpeg) against section timings |
| `validate_writing.py` | Task 1 `visual_data` is consistent (e.g. chart series align with labels) |
| `scripts/check_migration_heads.py` | The Alembic migration graph has a single head |

**CI pipeline** (`.github/workflows/ci.yml`, runs on every push to `main` / `nurhan/**` and on every pull request):

| Job | Steps |
|-----|-------|
| `backend` | Python 3.12 + PostgreSQL 16 service → migration single-head check → `alembic upgrade head` → downgrade → upgrade again (migrations are reversible) → three content validators → `pytest -q` (with `AI_PROVIDER=mock`, so no paid calls) |
| `frontend` | Node 20 → `npm ci` → ESLint → `tsc --noEmit` → `vitest run` → `next build` |
| `compose-config` | Validates `docker-compose.prod.yml` with production-like variables |

Merge rule: a pull request is merged only when all three jobs are green. (`deploy.yml` is a legacy manual workflow. Production deploys through Render, `render.yaml`.)

### 9.1.2 Gaps and planned tests

| Planned test | Covers | Tool |
|--------------|--------|------|
| Unit tests for `recency_decay` (0.5 at 14 days), the recurring threshold (≥ 3 attempts) and band-gap rounding with no data | FR-8, FR-9 | pytest |
| **End-to-end tests** of Scenarios 1–5 (Section 8): register → set target → submit essay (mock grader) → see review → dashboard task → regrade → compare; Reading test → evidence review; save word → quiz | FR-1, 3–6, 9–13, 17 | Playwright against the CI stack (`AI_PROVIDER=mock`) |
| Mobile viewport tests at 390×844 (no horizontal scroll, navigation menu works) | NFR-11 | Playwright |
| API latency measurement on production (p50/p90/p99 of `/writing/submit`) | NFR-1 | server logs over ≥ 30 gradings |
| Load test: 20 concurrent gradings with a stubbed slow provider; `/health/live` must stay < 1 s | NFR-2 | Locust / k6 |

### 9.1.3 Security regression tests

These tests already run in CI and must never be removed. Each one protects against a specific failure:

| Risk | Regression test |
|------|-----------------|
| Forged or expired JWT, token reuse after username change | `test_auth_tokens.py` |
| OAuth code interception / CSRF / open redirect | `test_google_auth.py` (PKCE S256, single-use state, exact redirect match, verified email only) |
| Brute force, spoofed `X-Forwarded-For` | `test_ratelimit.py` |
| Production started with a weak or leaked `SECRET_KEY`, or with the mock grader | `test_ai_safety.py` |
| Quota bypass via parallel requests, retries or renaming | `test_ai_quota.py`, `test_writing_retry.py`, `test_vocabulary_quota.py` |
| Private audio served from a public path | `test_deploy_paths.py` |
| Personal data in ML exports | `test_ml_export_responses.py` |
| Another user's Reading data in the notebook | `test_personalized_learning.py` (ownership check) |

Planned additions: an IDOR test that checks every `/{id}` endpoint returns 404 for another user's object; secret scanning (gitleaks) in CI; and a dependency audit (`pip-audit`, `npm audit`).

## 9.2 Evaluation experiments

### E1 – Writing: LLM grading vs expert scores (TST-42, data TST-40)

| Item | Plan |
|------|------|
| **Research question** | How closely does the two-stage Gemini examiner agree with qualified IELTS examiners, overall and per criterion, and is it stable across repeated runs? |
| **Data** | Labelled Task 1 and Task 2 essays with expert band scores (overall + 4 criteria), from published examiner-scored sample answers (where reuse is permitted) and essays scored by certified teachers (TST-40). Planned size: **≥ 100 essays**, spread over bands 4–8. A seed bank of anchor cases already exists: `backend/tests/fixtures/writing_calibration.md`, with bands 4–8 plus cap cases: off-topic, under-length, fabricated data, no overview. Data stays outside git (`*.local.jsonl`). |
| **Metrics** | MAE (overall and per criterion); **Quadratic Weighted Kappa (QWK)** on half-band labels; % exact agreement and **% within ±0.5 band**; cap-case hit rate. **Stability:** each essay graded 5 times → standard deviation of the overall band, and % of essays whose band changes between runs. |
| **Measurement conditions** | Production configuration: `gemini-2.5-flash`, examiner temperature 0.1, the same prompts as production. Coach stage disabled (`WRITING_COACH_ENABLED=false`) so only the grade is measured. Run with `scripts/run_writing_calibration.py --tolerance 0.5 --report ...`. Prompts and model version are frozen during the run, and the report is saved. Expert labels are hidden from the prompt. |
| **Baselines** | (1) **Mean predictor** (always the dataset's mean band). (2) The **deterministic heuristic grader** (`ai/mock.py`, the free fallback used in development). (3) **Ridge regression on text features** (length, type/token ratio, sentence length, error counts), cross-validated on the same essays. |
| **Success thresholds (targets)** | Overall MAE ≤ 0.5. **QWK ≥ 0.6** overall (≥ 0.5 per criterion). ≥ 70% of essays within ±0.5 band. Cap cases fire in ≥ 90% of cases. Std of the overall band across 5 runs ≤ 0.25. The LLM must beat all baselines on MAE and QWK. |

### E2 – Speaking: ASR quality and score model (TST-46, data TST-45)

| Item | Plan |
|------|------|
| **Research question** | (a) Which Whisper model size gives acceptable transcription for L2 English speakers at an acceptable speed on CPU? (b) Can fluency features + a regressor predict expert Speaking bands better than simple baselines? |
| **Data** | Recorded Speaking answers (Parts 1–3) from consenting volunteers, with reference transcripts and expert band labels (TST-45). Stored pseudonymously in the `speaking.v1` schema (`ml/data.py`). Raw audio is never committed. Planned size: **≥ 30 speakers / ≥ 150 answers**. |
| **Metrics** | (a) Corpus **WER** (normalisation v1, `ml/metrics.py`), real-time factor and model load time per model. (b) **MAE, QWK** (half-band), % within ±0.5 band. |
| **Measurement conditions** | (a) `python -m ml.benchmark_asr` with `tiny.en` vs `base.en` (optionally `small.en`), CPU, int8. (b) `ml.train_speaking`: **speaker-disjoint** hold-out split (no speaker in both train and test), seed 42, test size 25%. Features `fluency.v1` (speech rate, articulation rate, pauses, fillers, repetitions, repairs, ASR confidence). |
| **Baselines** | **Mean predictor** (`DummyRegressor`). The **LLM transcript/audio grade** (current Gemini grader) on the same test speakers. Compared with linear regression and gradient boosting. |
| **Success thresholds (targets)** | WER ≤ 15% for the chosen model with real-time factor < 1 on CPU. Score model: **QWK ≥ 0.6**, MAE ≤ 0.6, and better than the mean baseline. Speaking is enabled in the UI (TST-48) only if the production grader reaches these targets. |

### E3 – Adaptive practice: predicting correct answers (TST-47)

| Item | Plan |
|------|------|
| **Research question** | Do the Rasch/IRT difficulty model and Bayesian Knowledge Tracing predict whether a learner answers the next Reading/Listening question correctly better than a simple error rate? (A model that predicts better can choose better-targeted practice.) |
| **Data** | Real Reading/Listening responses exported with `python -m ml.export_responses` (pseudonymous keyed IDs, no names/emails/answer text, content versions kept). Planned: ≥ 50 learners, ≥ 5,000 responses. |
| **Metric** | **ROC AUC** of P(correct). Brier score / log-loss as secondary metrics. |
| **Measurement conditions** | `ml.evaluate_adaptive`: **chronological split** (first 75% of responses for training, last 25% for testing), predict-before-update, repeated attempts excluded. The cold-start subset (learners with < 5 responses) is reported separately. |
| **Baseline** | **Error-rate baseline**: the smoothed historical correct rate `(successes + 1)/(total + 2)`. |
| **Success threshold (target)** | IRT or the IRT+BKT blend reaches **AUC ≥ 0.70** and beats the baseline by **≥ 0.03 AUC**. If it does not, the adaptive ranking stays in research and is not shipped. |

### E4 – User pilot: does the coach loop help?

| Item | Plan |
|------|------|
| **Research question** | Do learners who follow the loop (grade → blocker → task for today → regrade) improve their Writing band, and do they find the feedback useful and the product usable? |
| **Participants** | **N ≥ 20** IELTS candidates (target band 6.0–7.5), recruited from AITU students and IELTS preparation groups, with informed consent. Recruitment criteria are aligned with the interviews (Section 2). |
| **Procedure** | 3–4 weeks. Initial essay → at least **K = 3 regrades** on comparable Task 2 prompts, following the task for today. Quota exemption for participants. Post-survey and a short interview. |
| **Metrics** | (1) **Band change** between the first and last graded essay (Testora score). For a subset of ≥ 10 participants, also scored blind by a human examiner to check it is not grader drift. (2) Share of participants whose named blocker criterion improves by ≥ 0.5. (3) **SUS** score. (4) Usefulness Likert items (1–5: "the blocker was accurate", "today's task was clear", "the Better Version helped"). (5) **Retention**: share active in week 2 and week 3; mean graded essays per participant. (6) Technical: grading failure rate and p90 latency (NFR-1, NFR-8). |
| **Measurement conditions** | Production site, the same model version for the whole pilot, comparable prompts per round, and anonymised analytics export. |
| **Baseline** | Within-subject: each participant's first essay. If enough people sign up, a comparison group that writes the same number of essays with a **score-only** review (band without blocker/task) will be used to separate the effect of the loop from the effect of practice alone. |
| **Success thresholds (targets)** | Median band change ≥ +0.5 after K regrades (confirmed by the human-scored subset). SUS ≥ 68 (above average). Mean usefulness ≥ 4.0/5. ≥ 50% of participants active in week 2. Grading failure rate < 2%. |

## 9.3 How the aim will be demonstrated

| Aim component | Evidence at the defence |
|---------------|-------------------------|
| The system works as specified | Green CI run (162 backend test functions + 41 frontend test cases, validators, build) and the live demo of Scenarios 1–5 on testora.studio |
| The grading is trustworthy | E1 report: MAE/QWK/±0.5 agreement vs baselines, per criterion, and the stability table |
| The ML components add value | E2 (WER, speaker-disjoint QWK) and E3 (AUC vs error-rate baseline). Components that do not meet targets are reported as negative results and stay out of the product |
| Learners benefit | E4: band change, SUS, usefulness, retention |
| Security and reliability | Security regression suite (9.1.3) and the failed-grade handling (NFR-8) shown in the demo |

**Risks to the evaluation:** a small labelled dataset (results will be reported with 95% bootstrap confidence intervals), noise in expert labels (we will report inter-rater agreement wherever two experts scored the same essay), and model updates by the provider (the model version is fixed for the duration of each experiment).
