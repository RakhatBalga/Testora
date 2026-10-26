# Testora: orientation for coding assistants

Short map of the repository. The authoritative description is in `docs/` (sections 01–11 of the
diploma report) and in the code. Update this file when the architecture changes.

## What it is
Testora is an AI IELTS coach. The product loop: **grade → extract mistakes → name the band
blocker → tell the user what to do today → re-grade → show the band move.** Analytics are pure
aggregation over stored data; the LLM is called only at grading time.

## Stack and production
- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind v4, `frontend/`. Hosted on Vercel.
- **Backend:** FastAPI + SQLAlchemy + Alembic, `backend/`. Docker image on Render (`render.yaml`,
  free plan: sleeps when idle, cold start about a minute). Migrations run on boot (`start-render.sh`).
- **Database:** PostgreSQL on Neon. No Supabase.
- **AI:** Gemini in production (`AI_PROVIDER=gemini`), behind `backend/app/infrastructure/ai/`
  (`mock | claude | gemini | qwen`, see `factory.py`). `mock` is for development and CI only;
  the API refuses to start in production on the mock grader. A self-hosted Qwen model
  (OpenAI-compatible server, `AI_PROVIDER=qwen`, guide: `docs/qwen.md`, serving configs in `ai/`) is implemented
  and selectable by env, but not used in production and not yet measured: it replaces Gemini only if
  experiment E1 (docs/09) shows comparable accuracy.
- CI is `.github/workflows/ci.yml`; Render deploys `main` after the checks pass. Details: `docs/operations.md`.

## How to run locally
- Full stack with the mock grader: `docker compose up --build` (frontend :3000, API :8000).
- Or by hand: `cd backend && cp .env.example .env && alembic upgrade head && uvicorn app.main:app --reload`
  (needs PostgreSQL), and `cd frontend && npm ci && npm run dev` with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- Demo data (refuses to run against production): `cd backend && python -m scripts.seed.seed_demo`.
- Checks: backend `pytest` (from `backend/`), frontend `npm run lint && npm run typecheck && npm run test:run && npm run build`.
- Auth is username + password or Google sign-in; the JWT is kept in `sessionStorage`.

## Backend layout (`backend/app/`)
- `domain/`: SQLAlchemy models and pure scoring/band logic.
- `application/`: use-case services (writing, speaking, attempts, accounts, google_auth, quota, ai_gate,
  mistakes, analytics/, learning/, listening/, ...).
- `api/`: thin FastAPI routers, dependencies, Pydantic schemas.
- `infrastructure/`: database, config, security, rate limiting, storage, logging, error tracking and
  `ai/` (graders, prompts, schemas). `ai/base.py` = `Feedback` + `MistakeItem`; `ai/factory.py` picks the provider.
- `backend/content_tools/`: content importer and validators (`python -m content_tools.importer`,
  `python -m content_tools.validate_reading`, ...). `backend/scripts/seed/`, `backend/scripts/dev/`: seeding and dev tools.
- `backend/ml/`: research code (Speaking ASR and features, IRT, knowledge tracing, Writing evaluation E1).
  Not imported by the production grading path.

## Frontend layout (`frontend/src/`, Feature-Sliced Design)
`app/` (routes) → `widgets/` → `features/` → `entities/` → `shared/` (api client, auth, ui, config).
Imports go downwards only and through each slice's `index.ts`; ESLint enforces it. Backend access goes
through `shared/api`; pages and features do not call `fetch` directly. Layout details: `frontend/README.md`.

## Conventions
- Keep API contracts and routes stable unless the task says otherwise.
- Work happens on branches `TST-<id>-short-name` with pull requests; `main` is protected (checks
  `backend`, `frontend`, `compose-config` must pass).
- Documentation is English. The numbered files `docs/01-…11-*.md` are report sections: edit them,
  do not rename or delete them. Do not put secrets in the repository.

## Scope
IELTS only; web app; no other exams, no native apps, no social features. Speaking is gated off in the
UI (`SPEAKING_AVAILABLE`) and on the server (`SPEAKING_ENABLED=false` in production).
