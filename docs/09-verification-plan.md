# 9. Verification and Evaluation Plan

The project aim is to build an IELTS preparation system that (a) grades Writing (and later Speaking) close to expert examiners, (b) correctly identifies what keeps a learner's band from rising, and (c) helps learners improve. We demonstrate this at two levels:

1. **Verification:** the system does what Section 6 specifies. This is checked by automated tests in CI, content validators, and scripted security and end-to-end checks.
2. **Evaluation:** the system is good enough to be useful. This is checked by four experiments (E1–E4), each with a research question, data, metric, measurement conditions, a baseline, and a success threshold.

> **Honest status (26 October 2026):** no accuracy or pilot results exist yet. The measurement code is in place (`backend/ml/`: dataset builder, collector, evaluator and trained baselines for Writing; ASR, Speaking and adaptive evaluation), but the labelled datasets are still being collected (YouTrack **TST-40**: Writing dataset, **TST-45**: Speaking dataset). The 8-essay development bank is not a test set (the prompt was tuned on it), so any score on it is not evidence of accuracy. All thresholds below are **targets**, not achieved results.

## 9.1 Testing plan

### 9.1.1 Existing automated tests

Counts were taken on 26 October 2026 from the integration branch: `def test_*` functions in the backend (`grep -c "def test_"`), `pytest --collect-only` for the number of cases after parametrisation, and `npx vitest run` for the frontend. Recount before every submission.

**Backend – pytest: 51 test files, 391 test functions, 541 collected cases** (`backend/tests/`; a few PostgreSQL-only tests are skipped on SQLite)

| Area | Test files (number of test functions) |
|------|---------------------------------------|
| LLM Writing grading | `test_writing_examiner.py` (59), `test_gemini_grading.py` (21), `test_qwen_grading.py` (16), `test_qwen_client.py` (20), `test_writing_precheck.py` (4), `test_writing_retry.py` (4) |
| Coach loop / analytics | `test_analytics_core.py` (8), `test_personalized_learning.py` (6), `test_recommendations.py` (2), `test_weekly_analytics.py` (1), `test_target_band.py` (8), `test_band.py` (6), `test_response_models.py` (3) |
| Reading / Listening / content | `test_reading_scoring.py` (4), `test_reading_catalog.py` (3), `test_listening_scoring.py` (6), `test_listening_updates.py` (4), `test_listening_validator.py` (4), `test_content_pipeline.py` (9), `test_seed_demo_guard.py` (3) |
| Vocabulary | `test_vocabulary.py` (4), `test_vocabulary_quota.py` (3) |
| Security & reliability | `test_auth_tokens.py` (3), `test_google_auth.py` (5), `test_ratelimit.py` (2), `test_request_limits.py` (10), `test_ai_safety.py` (12), `test_ai_quota.py` (6), `test_reliability.py` (24), `test_storage_and_uploads.py` (12), `test_deploy_paths.py` (3) |
| ML research modules | `test_ml_asr.py` (1), `test_ml_benchmark_asr.py` (4), `test_ml_data.py` (3), `test_ml_speech_features.py` (3), `test_ml_train_speaking.py` (10), `test_ml_metrics.py` (6), `test_ml_irt.py` (2), `test_ml_knowledge_tracing.py` (3), `test_ml_recommendation.py` (2), `test_ml_evaluate_adaptive.py` (7), `test_ml_export_responses.py` (6) |
| E1 Writing evaluation tooling (`tests/ml/`) | `test_writing_data.py` (8), `test_writing_stats.py` (11), `test_writing_collect.py` (6), `test_writing_train.py` (5), `test_writing_evaluate.py` (8), `test_writing_integrity.py` (14); dataset readiness and record safety in `tests/ml/datasets/` (`test_readiness.py` 11, `test_speaking_readiness.py` 3, `test_record_safety.py` 3) |

**Frontend – Vitest + Testing Library: 22 files, 108 tests** (`npx vitest run`)

`app/listening/progress.test.tsx`, `app/login/page.test.tsx`, `entities/profile/model/stats.test.ts`, `entities/test/model/routes.test.ts`, `entities/test/model/storage.test.ts`, `features/auth/model/googleFlow.test.ts`, `features/auth/ui/GoogleSignInButton.test.tsx`, `features/feedback/ui/ReviewStatusNotice.test.tsx`, `features/listening-session/model/progress.test.ts`, `features/listening-session/ui/ListeningAudioPlayer.test.tsx`, `shared/api/login.test.ts`, `shared/api/quotaErrors.test.ts`, `shared/api/request.test.ts`, `shared/lib/band.test.ts`, `shared/lib/examTimer.test.ts`, `shared/lib/formatDisplayName.test.ts`, `shared/lib/greeting.test.ts`, `shared/lib/micError.test.ts`, `shared/lib/safeNext.test.ts`, `shared/lib/useDeadlineCountdown.test.tsx`, `shared/lib/useExamTimer.test.tsx`, `shared/ui/Button.test.tsx`.

**Content validators** (run as `python -m content_tools.validate_<name>` from `backend/`; in CI before the tests):

| Validator | What it checks |
|-----------|----------------|
| `content_tools/validate_reading.py` | Every question (except "Not Given") has evidence with paragraph, sentence and a quote found **verbatim** in the passage. Answer keys and question types are well-formed |
| `content_tools/validate_listening.py` | Test structure, evidence quotes in transcripts, and the **real audio duration** (ffmpeg) against section timings |
| `content_tools/validate_writing.py` | Task 1 `visual_data` is consistent (e.g. chart series align with labels) |
| `scripts/dev/check_migration_heads.py` | The Alembic migration graph has a single head |

**CI pipeline** (`.github/workflows/ci.yml`, runs on every push to `main` / `nurhan/**` and on every pull request):

| Job | Steps |
|-----|-------|
| `backend` | Python 3.12 + PostgreSQL 16 service → ruff (syntax errors and undefined names) → migration single-head check → `alembic upgrade head` → downgrade → upgrade again (migrations are reversible) → `alembic check` (models match migrations, blocking) → three content validators → `pytest -q` (with `AI_PROVIDER=mock`, so no paid calls) |
| `frontend` | Node 20 → `npm ci` → ESLint → `tsc --noEmit` → `vitest run` → `next build` |
| `backend-image` | Builds the backend Docker image (no push) |
| `compose-config` | Validates `docker-compose.yml` (defaults and production-like variables, `qwen` profile) |

Merge rule: since 26 October 2026 branch protection on `main` requires the checks `backend`, `frontend` and `compose-config`, and blocks force-push and deletion. Approvals are not required by the protection rule. Production deploys through Render (`render.yaml`, `autoDeployTrigger: checksPass`), i.e. only after the checks for the commit pass. Before that date, Render deployed every push without waiting for CI and no rule enforced green checks. Dependabot proposes dependency updates weekly (pip, npm, GitHub Actions, Docker).

**Provider tests.** The Qwen client and grading pipeline are tested against fake servers (`test_qwen_client.py`, `test_qwen_grading.py`); no real model or paid API is called in CI.

**Code review.** The workflow asks for a review of every pull request by the other team member. In practice only a few pull requests so far carry a recorded review (the documentation pull request was reviewed and approved); most earlier ones were merged by their author. Mandatory approvals are not enforced yet and are planned once the workflow in Section 10 is in regular use.

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
| **Data** | Labelled Task 1 and Task 2 essays with expert band scores (overall + 4 criteria), from published examiner-scored sample answers (where reuse is permitted) and essays scored by certified teachers (TST-40). Planned size: **≥ 100 essays**, spread over bands 4–8. A small development bank of anchor cases already exists (`backend/tests/fixtures/writing_calibration_bank.jsonl`, 8 essays; descriptions in `backend/tests/fixtures/writing_calibration.md`) with bands 4–8 plus cap cases: off-topic, under-length, fabricated data, no overview. It is the `dev` split only: the prompt was tuned on it, so it is never used as a test set. The evaluation set is a public scored-essay corpus (single, non-certified raters, possibly seen by the LLM during training: a noisy-label benchmark with contamination risk, reported as such) plus a double-marked teacher set (`gold`). The dataset builder (`ml/writing_data.py`, schema `writing-essay.v1`) removes exact and near-duplicates and splits by prompt group, so no prompt appears in both train and test; a manifest records sources, licences and skipped rows. Private data stays outside git (`*.local.jsonl`). |
| **Metrics** | MAE (overall and per criterion); **Quadratic Weighted Kappa (QWK)** on half-band labels; % exact agreement and **% within ±0.5 band**; cap-case hit rate. Also bias (mean signed error), prediction spread and mode share (a flat predictor can have a respectable MAE and QWK near 0, so these are read together), RMSE, Pearson/Spearman, coverage (share of essays graded successfully) and 95% bootstrap confidence intervals, plus paired bootstrap differences between systems. **Stability:** each gold essay graded 5 times → standard deviation, intraclass correlation (ICC) and % of essays whose band changes between runs. **Human ceiling:** agreement between the two teachers on the gold set. |
| **Measurement conditions** | Production configuration: `gemini-2.5-flash`, examiner temperature 0.1, the same prompts as production. Coach stage disabled (`WRITING_COACH_ENABLED=false`) so only the grade is measured. The pipeline (documented in `backend/calibration/README.md`, "How to run E1"): `ml.writing_data` → `ml.train_writing` → `ml.collect_writing` (cached, resumable, failures recorded and retried, `--runs N`) → `ml.evaluate_writing`. A provider that is not actually configured is refused instead of silently falling back to the mock grader. **Pre-registration:** the model, prompts, primary metric and thresholds are written down (`calibration/PREREGISTRATION_TEMPLATE.md`, generated with `--write-prereg`) and committed before the test split is evaluated; evaluating `test` or `gold` without it is flagged in the report. Every graded result records `provider`, `model` and `prompt_version` in its feedback diagnostics, and the E1 collection cache key includes `prompt_version`, so runs made under different prompt versions are kept apart. Prompts and model version are frozen during the run, and the report (`ml/reports/*.md/.json`) is saved. Expert labels are hidden from the prompt. The same protocol is run for a locally hosted Qwen model (`--provider qwen`) next to Gemini, so that the planned replacement is judged on the same essays with the same thresholds. |
| **Baselines** | (1) **Mean predictor** (always the dataset's mean band). (2) The **deterministic heuristic grader** (`ai/mock.py`, the free fallback used in development). (3) **Trained text-feature baselines**: Ridge regression and gradient boosting on features such as length, type/token ratio and sentence length (`ml/train_writing.py`), with prompt-grouped cross-validation and evaluated on the same test split. (4) Constant mean and mode predictors as sanity floors. |
| **Success thresholds (targets)** | Overall MAE ≤ 0.5. **QWK ≥ 0.6** overall (≥ 0.5 per criterion). ≥ 70% of essays within ±0.5 band. Cap cases fire in ≥ 90% of cases. Std of the overall band across 5 runs ≤ 0.25. The LLM must beat all baselines on MAE and QWK. A candidate replacement model (Qwen, implemented but not yet measured) is accepted only if it also meets these thresholds and is not significantly worse than Gemini on the paired bootstrap difference. |

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
| The system works as specified | Green CI run (467 backend test cases + 102 frontend tests, validators, build) and the live demo of Scenarios 1–5 on testora.studio |
| The grading is trustworthy | E1 report: MAE/QWK/±0.5 agreement vs baselines, per criterion, and the stability table |
| The ML components add value | E2 (WER, speaker-disjoint QWK) and E3 (AUC vs error-rate baseline). Components that do not meet targets are reported as negative results and stay out of the product |
| Learners benefit | E4: band change, SUS, usefulness, retention |
| Security and reliability | Security regression suite (9.1.3) and the failed-grade handling (NFR-8) shown in the demo |

**Risks to the evaluation:** a small labelled dataset (results will be reported with 95% bootstrap confidence intervals), noise in expert labels (we will report inter-rater agreement wherever two experts scored the same essay), and model updates by the provider (the model version is fixed for the duration of each experiment).
