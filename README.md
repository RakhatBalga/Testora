# Testora — AI IELTS Coach

**Diploma project:** Development of an Intelligent IELTS Exam Preparation System Based on Large Language Models and Machine Learning Methods (Testora).
Astana IT University, Software Engineering, 2026–2027.

Live prototype: **https://testora.studio** · YouTrack: **https://testora-diploma.youtrack.cloud** (project `TST`) · Documentation: [`docs/`](docs/)

## Problem
IELTS candidates who prepare on their own lack affordable, explainable feedback on Writing and Speaking. Existing trainers give a band per attempt, but not *why* the band is stuck and what to do next.

## Target users
People worldwide preparing for IELTS (Academic / General Training) for study, work or immigration — primarily budget-limited self-learners.

## What Testora does
Grade → extract mistakes → name the band blocker → tell the user what to do today → re-grade → show the band move.
- LLM-based Writing assessment on the four IELTS criteria with mistake extraction (Gemini in production behind a provider-independent layer).
- Weakness model (recency-weighted mistakes, 14-day half-life) and band gap → task for today.
- Reading and Listening tests with automatic checking and verbatim evidence for every answer.
- Research modules: Speaking assessment (Whisper ASR, fluency features, score regression) and adaptive practice (Rasch/IRT, knowledge tracing).

## Expected outcomes
A deployed platform with the full coach loop, integrated Speaking and adaptive modules, and an experimental report on assessment quality (MAE, QWK, ±0.5 band agreement vs expert scores; WER; AUC) plus a user pilot.

## Team
| Member | GitHub | Responsibilities |
|---|---|---|
| Rakhat Balgabekov | [@RakhatBalga](https://github.com/RakhatBalga) | LLM-based assessment core (Writing), weakness model and personalization, architecture, backend, deployment |
| Nurhan Turganbek | [@nurhan-ghost](https://github.com/nurhan-ghost) | Speaking ML module, adaptive Reading/Listening practice, security and reliability, practice UI, content, testing |
| Supervisor: Tomiris Zhaksylyk | — | Supervision and review |

## Scope and current status (October 2026)
- **In scope:** IELTS only, web app (desktop + mobile browser), all four skills, AI assessment, personalization, experimental evaluation.
- **Out of scope:** other exams, native mobile apps, official score certification, social features.
- **Status:** platform deployed; Writing grading, Reading/Listening, weakness model v1 and the daily-task loop implemented. Speaking UI is temporarily disabled; Speaking ML and adaptive models exist as research code (integration planned). Accuracy against expert scores is not measured yet — datasets planned for Nov 2026. Details: [docs/10-project-management.md](docs/10-project-management.md).

## Documentation (probationary period)
The report sections below live on `main`. The submission tag will be re-cut on the commit that contains them (see [docs/10](docs/10-project-management.md)).

| # | Section | File |
|---|---|---|
| 1 | Project proposal | [docs/01-project-proposal.md](docs/01-project-proposal.md) |
| 2 | Evidence of relevance (user interviews) | [docs/02-evidence-of-relevance.md](docs/02-evidence-of-relevance.md) |
| 3 | Literature review | [docs/03-literature-review.md](docs/03-literature-review.md) |
| 4 | Existing systems comparison | [docs/04-existing-systems-comparison.md](docs/04-existing-systems-comparison.md) |
| 5 | Technology comparison | [docs/05-technology-comparison.md](docs/05-technology-comparison.md) |
| 6 | Requirements specification | [docs/06-requirements.md](docs/06-requirements.md) |
| 7 | Architecture and diagrams | [docs/07-architecture.md](docs/07-architecture.md) · sources in [docs/diagrams/](docs/diagrams/) |
| 8 | UX / prototype | [docs/08-ux-prototype.md](docs/08-ux-prototype.md) |
| 9 | Verification and evaluation plan | [docs/09-verification-plan.md](docs/09-verification-plan.md) |
| 10 | Project management and risks | [docs/10-project-management.md](docs/10-project-management.md) |
| 11 | Supervisor feedback | [docs/11-supervisor-feedback.md](docs/11-supervisor-feedback.md) |

## Repository structure
- `frontend/` — Next.js app (Feature-Sliced Design), see [frontend/README.md](frontend/README.md)
- `backend/` — FastAPI app (Clean Architecture), Alembic migrations, content packs (`content/`), content importer and validators (`content_tools/`), seed and dev scripts (`scripts/`), tests (`tests/`), ML research and evaluation code (`ml/`, `calibration/`)
- `docs/` — diploma documentation and the operations runbook ([docs/operations.md](docs/operations.md)); `docs/diagrams/` — editable diagram sources (`.mmd`, `.puml`) with PNG/SVG exports
- `scripts/` — database backup and restore helpers
- `ai/` — serving configuration for a locally hosted model (planned Qwen replacement)
- `.github/workflows/` — CI and the manual database-backup workflow; `render.yaml` — Render service definition; `docker-compose.yml` — local full stack
- `.env.example`, `backend/.env.example`, `frontend/.env.example` — configuration examples (no real secrets in the repo)

## Workflow
YouTrack task `TST-<id>` → branch `TST-<id>-short-name` → commits `TST-<id>: …` → pull request referencing the task → review by the other team member → merge to `main`. `main` is protected: the CI checks `backend`, `frontend` and `compose-config` must pass, and force-push and deletion are blocked (approvals are not required yet). Each submission is tagged (`prob-period-1`, `pre-defense-1`, …); submitted tags are not moved.

## Stack
- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind v4 — `frontend/`, hosted on Vercel
- **Backend:** FastAPI + SQLAlchemy + Alembic — `backend/`, Docker image on Render (free plan)
- **DB:** PostgreSQL on Neon
- **AI:** Gemini behind `backend/app/infrastructure/ai/` (`AI_PROVIDER=mock | claude | gemini`; production uses Gemini). A locally hosted Qwen model behind an OpenAI-compatible API is planned as a replacement once experiment E1 shows comparable accuracy; it is selected with `AI_PROVIDER=qwen`.

## Local development

### Full stack in Docker (mock grader)
```bash
docker compose up --build     # frontend http://localhost:3000, API http://localhost:8000
```

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then edit DATABASE_URL + SECRET_KEY
alembic upgrade head          # apply migrations
uvicorn app.main:app --reload --port 8000
```
API docs (development only): http://localhost:8000/docs · Health: http://localhost:8000/health/live

### Frontend
```bash
cd frontend
npm ci
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev                   # http://localhost:3000
```

## Configuration

Main variables (full list: `backend/.env.example`, `render.yaml`, [docs/operations.md](docs/operations.md)).

| Var | Where | Purpose |
|-----|-------|---------|
| `DATABASE_URL` | backend | Postgres connection string (required) |
| `SECRET_KEY` | backend | JWT signing secret — `openssl rand -hex 32` (required) |
| `APP_ENV` | backend | `production` enables the startup safety checks (no mock grader, strong secret) |
| `CORS_ORIGINS`, `FRONTEND_URL` | backend | Allowed browser origins and the public frontend URL |
| `TRUSTED_PROXY_CIDRS` | backend | Proxies whose `X-Forwarded-For` is trusted for rate limiting |
| `AI_PROVIDER` | backend | `mock`, `claude`, `gemini` (or `qwen`, planned) |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FAST_MODEL` | backend | Gemini key; examiner model; cheaper model for coach text and rewrites |
| `FREE_WRITING_SUBMISSIONS`, `FREE_SPEAKING_SUBMISSIONS`, `AI_DAILY_ATTEMPTS`, `AI_GLOBAL_DAILY_ATTEMPTS` | backend | Free-tier quota, per-user and global daily AI budget |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | backend | Google sign-in (the button also needs `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in the frontend build) |
| `STORAGE_BACKEND`, `SPEAKING_ENABLED` | backend | Avatars and audio storage (`database` or `local`); server-side Speaking gate |
| `APP_TIMEZONE` | backend | IANA tz for quota day, streaks, daily plan (default `Asia/Almaty`) |
| `SENTRY_DSN`, `LOG_LEVEL` | backend | Optional error tracking; log level |
| `NEXT_PUBLIC_API_URL` | frontend | Public backend URL, inlined at **build** time |

## Production deployment

Production is **Vercel (frontend) + Render (backend Docker image, `render.yaml`) + Neon (PostgreSQL)**.
- Render deploys `main` automatically, but only after the GitHub checks for the commit pass (`autoDeployTrigger: checksPass`).
- The container applies `alembic upgrade head` on every start, then runs uvicorn (`backend/start-render.sh`).
- Secrets (`DATABASE_URL`, `GEMINI_API_KEY`, `GOOGLE_*`, `SENTRY_DSN`) are set in the Render dashboard, not in the repo. `NEXT_PUBLIC_*` variables are set in Vercel.
- The free Render plan sleeps when idle; the first request after a pause can take about a minute (the frontend shows a waking-up message).

Step-by-step procedures (deploy, rollback, backups, env vars): [docs/operations.md](docs/operations.md).

`docker-compose.yml` runs the full stack locally; it can also be used for a self-hosted setup behind a TLS reverse proxy, but that is not how testora.studio runs.

### Pre-launch checklist
- [ ] `SECRET_KEY` is a fresh random value (not the example)
- [ ] `CORS_ORIGINS` lists the real frontend domain(s); `FRONTEND_URL` is set
- [ ] `TRUSTED_PROXY_CIDRS` matches the proxy in front of the API
- [ ] `NEXT_PUBLIC_API_URL` (Vercel) points at the public API origin
- [ ] `APP_ENV=production`
- [ ] `AI_PROVIDER=gemini` **and** `GEMINI_API_KEY` set (the API refuses to start in production if grading would fall back to mock)
- [ ] Google sign-in: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` on Render and `NEXT_PUBLIC_GOOGLE_CLIENT_ID` on Vercel
- [ ] Content imported and validated (see Tests below)
- [ ] A recent database backup exists (`scripts/backup_prod.sh`; there is no scheduled backup yet)

## Operational notes
- **Rate limiting** is in-process (per backend worker) with per-route limits. Render runs a single process; if you scale out, add proxy/CDN or Redis limiting. `X-Forwarded-For` is trusted only from `TRUSTED_PROXY_CIDRS`.
- **Auth tokens** are stored in `sessionStorage`, not persistent `localStorage`.
- **Avatars and Speaking recordings** are stored in PostgreSQL (`stored_files`, size-capped) by default (`STORAGE_BACKEND=database`), because the Render container disk is ephemeral. Recordings are served only to their owner through an authenticated endpoint.
- **Failed AI grades** are saved without a band (Writing `status="failed"`) and excluded from analytics — never as a Band 0.
- **Containers** run as non-root users.

## Tests

Backend (from `backend/`):
```bash
python -m content_tools.validate_reading
python -m content_tools.validate_listening      # needs ffmpeg/ffprobe for the audio check
python -m content_tools.validate_writing
python -m scripts.dev.check_migration_heads
pytest
```

Content import:
```bash
cd backend
python -m content_tools.importer              # imports content/**/*.json (skips files under _examples/)
python -m content_tools.importer --replace    # replace matching content without touching user attempts
```

Content packs live under `backend/content/reading/`, `listening/`, `writing/` and `speaking/`. Listening audio is stored under `backend/static/audio/listening/` and referenced as `/static/...` URLs in the JSON. Academic Task 1 prompts use `visual_data` for locally rendered line, bar, table, pie, process, and map visuals; run the Writing validator before importing them. Demo data: `python -m scripts.seed.seed_demo` (refuses production databases).

Frontend (from `frontend/`):
```bash
npm run lint && npm run typecheck && npm run test:run
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build
```

Compose sanity: `docker compose config`.

Backups (PostgreSQL on Neon, see [docs/operations.md](docs/operations.md)):
```bash
DATABASE_URL=postgresql://... scripts/backup_prod.sh
DATABASE_URL=<target> scripts/restore_prod.sh <backup.dump.gz> --yes     # a production-looking target also needs --target-is-prod
```
