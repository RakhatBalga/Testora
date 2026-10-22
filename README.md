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
- LLM-based Writing assessment on the four IELTS criteria with mistake extraction (Gemini, provider-independent layer).
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

## Documentation (probationary period, tag `prob-period-1`)
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
- `frontend/` — Next.js app (Feature-Sliced Design)
- `backend/` — FastAPI app (Clean Architecture), Alembic migrations, content packs, tests (`backend/tests`), ML research code
- `docs/` — diploma documentation; `docs/diagrams/` — editable diagram sources (`.mmd`, `.puml`) with PNG/SVG exports
- `.github/workflows/` — CI
- `.env.example`, `backend/.env.example` — configuration examples (no real secrets in the repo)

## Workflow
YouTrack task `TST-<id>` → branch `TST-<id>-short-name` → commits `TST-<id>: …` → pull request referencing the task → review by the other team member → merge to `main`. Each submission is tagged (`prob-period-1`, `pre-defense-1`, …); submitted tags are not moved.

## Stack
- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind v4 — `frontend/`
- **Backend:** FastAPI + SQLAlchemy + Alembic — `backend/`
- **DB:** PostgreSQL
- **AI:** Gemini Flash behind `backend/app/infrastructure/ai/` (`mock | claude | gemini`; production uses Gemini)

## Local development

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit DATABASE_URL + SECRET_KEY
alembic upgrade head          # apply migrations
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs · Health: http://localhost:8000/health

### Frontend
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev                   # http://localhost:3000
```

## Configuration

| Var | Where | Purpose |
|-----|-------|---------|
| `DATABASE_URL` | backend | Postgres connection string (required) |
| `SECRET_KEY` | backend | JWT signing secret — `openssl rand -hex 32` (required) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | Token lifetime; default 1440 (24h) |
| `CORS_ORIGINS` | backend | Comma-separated allowed browser origins |
| `APP_TIMEZONE` | backend | IANA tz for streaks / daily plan (default `Asia/Almaty`) |
| `MAX_AUDIO_UPLOAD_MB` | backend | Speaking upload ceiling (default 15) |
| `MAX_WRITING_CHARS` | backend | Writing length ceiling (default 20000) |
| `AI_PROVIDER` | backend | `mock`, `claude`, or `gemini` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | backend | Required when `AI_PROVIDER=gemini` |
| `LOG_LEVEL` | backend | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `NEXT_PUBLIC_API_URL` | frontend | Public backend URL, inlined at **build** time |

See `.env.example` (root, for Docker) and `backend/.env.example` (local).

## Production deployment (Docker)
```bash
cp .env.example .env          # fill in real secrets + domains
docker compose -f docker-compose.prod.yml up -d --build
```
This starts Postgres, the API (runs `alembic upgrade head` on boot), and the
frontend. Put a TLS-terminating reverse proxy (nginx/Caddy/Traefik) in front of
ports 3000 (frontend) and 8000 (API).

### Pre-launch checklist
- [ ] `SECRET_KEY` is a fresh random value (not the example)
- [ ] `CORS_ORIGINS` lists the real frontend domain(s)
- [ ] `TRUSTED_PROXY_CIDRS` matches your reverse proxy / Docker bridge source
- [ ] `NEXT_PUBLIC_API_URL` points at the public API origin
- [ ] `APP_ENV=production`
- [ ] `AI_PROVIDER=gemini` **and** `GEMINI_API_KEY` set (the API refuses to start
      in production if grading would fall back to mock)
- [ ] Reading pack imported and validated: `cd backend && python validate_reading.py`
- [ ] Listening pack imported and validated: `cd backend && python validate_listening.py`
- [ ] Practice content imported:
      `docker compose -f docker-compose.prod.yml exec backend python import_content.py`
- [ ] Backups configured: `scripts/backup_prod.sh` writes DB + audio archives

## Operational notes
- **Rate limiting** is in-process (per backend worker). The Docker deploy runs a
  single backend process; if you scale workers/replicas, add proxy/CDN or Redis
  limiting for a global cap. `X-Forwarded-For` is trusted only from
  `TRUSTED_PROXY_CIDRS`.
- **Auth tokens** are stored in `sessionStorage`, not persistent `localStorage`.
- **Recordings** are stored privately under `backend/private/audio_submissions`
  and served only to their owner via an authenticated endpoint. The frontend
  fetches recordings with an Authorization header and plays a blob URL, so JWTs
  are not placed in query strings.
- **Failed AI grades** are saved without a band (Writing `status="failed"`) and
  excluded from analytics — never as a Band 0.
- **Containers** run as non-root users; keep mounted volumes writable by the
  container users.

## Tests

Backend:
```bash
cd backend
python validate_reading.py
python validate_listening.py
python validate_writing.py
python scripts/check_migration_heads.py
pytest
```

Content import:
```bash
cd backend
python import_content.py              # imports content/**/*.json
python import_content.py --replace    # replace matching content without touching user attempts
```

Content packs currently live under `backend/content/reading/`,
`backend/content/listening/`, `backend/content/writing/`, and
`backend/content/speaking/`. Listening audio
assets are stored under `backend/app/static/audio/listening/` and referenced as
`/static/...` URLs in the JSON. Academic Task 1 prompts use `visual_data` for
locally rendered line, bar, table, pie, process, and map visuals; run the
Writing validator before importing them.

Frontend:
```bash
cd frontend
npm run lint
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build
```

Production compose sanity:
```bash
POSTGRES_PASSWORD=dummy SECRET_KEY=dummy AI_PROVIDER=gemini GEMINI_API_KEY=dummy \
CORS_ORIGINS=https://app.testora.com NEXT_PUBLIC_API_URL=https://api.testora.com \
docker compose -f docker-compose.prod.yml config
```

Backups:
```bash
BACKUP_DIR=/backups/testora scripts/backup_prod.sh
# Restore:
scripts/restore_prod.sh /backups/testora/testora_db_YYYYmmddTHHMMSSZ.dump \
  /backups/testora/testora_audio_YYYYmmddTHHMMSSZ.tgz
```
