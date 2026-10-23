# 10. Project Management and Risks

## 10.1 Tools and traceability
| Tool | Link | Use |
|---|---|---|
| Git repository | https://github.com/RakhatBalga/Testora | Source code, documentation, diagrams, tests. `main` is the reviewed baseline; changes go through feature branches and pull requests |
| YouTrack | https://testora-diploma.youtrack.cloud (project **TST**) | Tasks with assignee, priority, deadline, expected outcome, acceptance criteria and links to commits/PRs; Kanban board |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | Backend tests, frontend lint/tests, content validators, security regression tests |
| Production | https://testora.studio | Live prototype for demonstrations and the pilot |

**Workflow (from this stage on):** one YouTrack task per meaningful work item → branch `TST-<id>-short-name` → commits `TST-<id>: description` → pull request that references the task and explains how the change was checked → review by the other team member → merge to `main` → task closed only when its acceptance criteria are met. Each submission is tagged (`prob-period-1`, then `pre-defense-1`, `pre-defense-2`, `final-pre-defense`); tags are never moved after submission.

**Note on history:** development started on 21 June 2026 (first commit). Work before October 2026 was tracked in Git history and pull requests; it was entered into YouTrack retroactively as tasks TST-17…TST-38 and TST-51…TST-76 with links to the original commits and their real dates. From October 2026 all work is planned in YouTrack first.

## 10.2 Allocation of responsibilities
| Area | Rakhat Balgabekov | Nurhan Turganbek |
|---|---|---|
| LLM-based Writing assessment, calibration, accuracy experiment | **Responsible** | Review |
| Weakness model, band gap, recommendations | **Responsible** | Review |
| Architecture, backend, deployment, CI/CD | **Responsible** | Contributes (security, CI) |
| Speaking ML module (ASR, features, score model) | Review | **Responsible** |
| Adaptive Reading/Listening (IRT, knowledge tracing) | Review | **Responsible** |
| Security and reliability hardening | Contributes | **Responsible** |
| Practice UI, content quality, e2e tests, pilot | Contributes | **Responsible** |
| Report chapters | Method, experiment, architecture | Speaking, adaptive, testing |

## 10.3 Milestones
| # | Period | Milestone | Deliverables | YouTrack |
|---|---|---|---|---|
| M0 | Jun – Oct 2026 | Working prototype | Deployed platform, Writing LLM grading, Reading/Listening, weakness model v1; Speaking and adaptive research code | TST-17…TST-38, TST-51…TST-76 (done) |
| M1 | 24 Oct 2026 | Probationary period submission | Proposal, evidence, literature review, comparisons, requirements, diagrams, prototype, evaluation plan, YouTrack, supervisor feedback | TST-1…TST-16 |
| M2 | Nov 2026 | Data and analysis | Labeled Writing essays and Speaking recordings with expert scores; literature review finalized | TST-39, TST-40, TST-45 |
| M3 | Dec 2026 – Jan 2027 | Integration | Weakness model with decay and band-gap forecast; Speaking and adaptive modules integrated; practice UI | TST-41, TST-48 |
| M4 | Feb – Mar 2027 | Experiments and pilot | Writing accuracy experiment, LLM comparison, Speaking validation, adaptive AUC evaluation, user pilot | TST-42, TST-43, TST-46, TST-47, TST-50 |
| M5 | Apr 2027 | Testing and report | E2E tests, fixes, explanatory note chapters | TST-44, TST-49 |
| M6 | May 2027 | Pre-defense and defense | Final tag, presentation, demo | — |

Supervision: weekly meeting with the supervisor; a demo of the working version every two weeks.

## 10.4 Risks
| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Not enough expert-scored essays/recordings for a reliable accuracy experiment | Medium | High | Combine public scored datasets with essays scored by certified teachers; start collection in November; report confidence intervals |
| R2 | LLM grading is unstable across runs or drifts after provider model updates | Medium | High | Fixed model version and temperature, schema-validated output, repeated-run stability test, provider-independent layer to switch models |
| R3 | LLM API cost or rate limits exceed the budget | Medium | Medium | Free-tier quota per user, atomic quota reservation, cheaper model for secondary tasks, caching |
| R4 | Whisper errors on accented speech reduce Speaking score quality | Medium | Medium | Compare model sizes by WER on our recordings; use ASR confidence as a feature; report error by accent where possible |
| R5 | Cold start: adaptive models have too few responses per item/user | High | Medium | Regularized Rasch model, explicit cold-start rules, error-rate baseline as fallback |
| R6 | Free hosting limits (sleep after inactivity, database limits, non-commercial frontend plan) affect the pilot | Medium | Medium | Warm-up before demos/pilot; move to a paid plan or a single VPS if needed (section 5) |
| R7 | Personal data and recordings leak | Low | High | Recordings stored privately and served only to the owner; pseudonymous ML export; secrets only in environment variables; security regression tests in CI |
| R8 | Workload imbalance or schedule slip in a two-person team | Medium | Medium | Weekly planning in YouTrack, clear ownership (10.2), review of each other's pull requests, re-planning at the weekly meeting |
| R9 | Interview/pilot participants are hard to recruit | Medium | Medium | Recruit among students preparing for IELTS; short sessions; incentives such as free extended gradings |

## 10.5 Dependencies
| Dependency | Type | Used for | Fallback |
|---|---|---|---|
| Google Gemini API | External service | Writing/Speaking assessment | Claude or OpenAI via the same provider interface; deterministic mock grader for development |
| Google OAuth | External service | Sign-in | Username + password login |
| Vercel, Render, Neon | Hosting | Frontend, backend, PostgreSQL | Docker Compose deployment on a single VPS (`docker-compose.prod.yml`) |
| OpenAI Whisper (open-source) | Library/model | Speaking transcription (research) | Cloud speech-to-text |
| Expert raters | People | Ground-truth band scores | Public scored datasets |
| Pilot users | People | Evaluation of usefulness | Smaller pilot with qualitative feedback |
