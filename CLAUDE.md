# Testora — AI orientation

Read this first. It tells you what the project is and how it's wired so you don't
have to explore the codebase. Keep it updated when architecture changes.

## What it is
Testora is an **AI IELTS Coach** (not just a practice app). The product is a loop:
**grade → extract mistakes → name the band blocker → tell the user what to do today →
re-grade → show the band move.** Target users: budget-conscious IELTS students in
Kazakhstan / CIS / MENA who can't afford private tutors. The dashboard is the center of
the product and must answer: (1) why isn't the user at their target band, (2) what should
they do next.

## Real stack (NOT what older docs/prompts assume)
- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind v4. In `frontend/`.
- **Backend:** FastAPI (Python) + SQLAlchemy + Alembic. In `backend/`.
- **DB:** PostgreSQL (local, `testora` db). Migrations via Alembic.
- **AI:** Gemini behind `backend/app/services/ai/` (factory: `mock | claude | gemini`).
  **Currently `AI_PROVIDER=mock`** — there is no AI budget, so all grading uses free
  deterministic heuristics. Switching to real Gemini later = env change only, no code edits.
- ⚠️ The product brief says "Supabase" — **the repo does NOT use Supabase.** Don't assume it.

## How to run
- Backend: `cd backend && venv/bin/uvicorn app.main:app --port 8000`
  (needs Postgres on :5432 and `backend/.env`). API docs at `/docs`.
- Frontend: dev server runs via the preview tooling (`.claude/launch.json`, name `frontend`,
  port 3000). Frontend talks to the API via `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- If the UI shows **"Failed to fetch"**, the backend isn't running — start uvicorn.
- Auth is username + password (JWT in localStorage). Test user: `Olzhas` / `testpass123`.

## Backend layout (`backend/app/`)
- `models/` — SQLAlchemy tables: `user`, `test`/`section`/`question`, `attempt` (reading/
  listening), `writing`, `speaking`, `mistake`.
- `routers/` — `auth`, `tests`, `results`, `writing`, `speaking`, `analytics`.
- `services/ai/` — grading abstraction. `base.py` = `Feedback` + `MistakeItem`; `mock.py` =
  free heuristic graders that ALSO emit deterministic, text-derived mistakes; `factory.py`
  picks the provider from env. **Grading creates mistakes.**
- `services/mistakes.py` — persists `MistakeItem`s to the `mistakes` table on submit.
- `services/analytics/` — **pure aggregation, NO AI at read time.** `sources.py` (uniform
  per-skill reads), `weakness.py` (weakness scoring + recurring detection), `band_gap.py`
  (band gap + blocker generation).
- Alembic: migrations in `backend/alembic/versions/`; register new models in `alembic/env.py`.

## Frontend layout (`frontend/src/`)
- `app/` — App Router pages: `/` (dashboard or landing), `login`, `register` (3-step
  onboarding), `practice/[skill]`, `mock-tests`, `analytics`, `vocabulary`, `writing`,
  `speaking`, `profile`, `tests/[type]`.
- `components/` — `ui/` (Button/Card/Badge/Input), `dashboard/` (widgets, BandTrajectory,
  WeaknessCard, BlockerCard), `auth/`, `landing/`.
- `lib/` — `api.ts` (typed FastAPI client — all backend calls go through here), `auth.tsx`
  (auth context), `coach.ts` (dashboard MOCK data + types, swappable for real endpoints),
  `dashboard.ts` (mock data for practice/analytics/vocab pages).

## Key domain model (the "coach loop")
1. User submits Writing/Speaking → graded by `services/ai` → `Feedback` (band + 4 IELTS
   criteria) + `MistakeItem[]`.
2. Mistakes saved to `mistakes` (skill, category, subskill, severity 1–3, snippet, correction).
3. **Weakness engine:** `score = 1 − 0.5^(Σ severity·recency_decay / opportunities)`,
   half-life 14 days. Recurring = appears in ≥3 recent attempts.
4. **Band gap:** overall = mean of per-skill bands rounded to 0.5; lowest skill = highest
   leverage; lowest criterion in Writing/Speaking = the named blocker.
5. Dashboard reads `/analytics/band-gap|blockers|weaknesses|recurring-mistakes` and shows
   the blocker + today's plan. Some dashboard sections (trajectory, today's plan, recent
   movement) are still mock from `lib/coach.ts`.

## Conventions
- **Design system:** blue academic palette via CSS vars in `globals.css`
  (`--brand #2563EB`, `--surface`, `--text-primary/secondary`, `--border`). No bright
  gradients, no gamification theatre. Reuse `ui/` and `dashboard/` components.
- **Mock data is centralized & swappable** (`lib/coach.ts`, `lib/dashboard.ts`) with
  `// BACKEND:` markers — replacing with real endpoints should need no UI change.
- Don't change auth fields/API contracts or existing routes unless asked.
- Verify UI changes in the browser preview; commit per feature with a clear message;
  end commit messages with the Co-Authored-By trailer.

## What's built vs not
- **Built:** landing, auth + onboarding, AI Coach dashboard (Phase 1), Writing grading
  (mock) with rubric + mistake extraction, Speaking practice (audio saved; mock grading),
  Mistake Memory v1 + Band Gap engine v1, practice/analytics/vocabulary pages (mock data).
- **Not built / partial:** real timed Reading/Listening mock-test interface, personal study
  plan, payments/subscriptions, real Gemini grading, RU/KZ localized explanations.

## Deeper docs (read only if relevant to your task)
- `docs/roadmap-ai-coach.md` — full feature roadmap (buckets, tables, 30-day plan, priority).
- `docs/ai-coach-redesign.md` — critical product review + dashboard/mistake-memory/band-gap design.
- `docs/architecture.md`, `docs/backend.md`, `docs/roadmap.md` — earlier architecture/MVP notes.

## Constraints (from the product owner)
- No paid AI right now → keep `AI_PROVIDER=mock`; don't propose solutions needing a paid API today.
- Don't migrate to Supabase, don't add other exams (SAT/TOEFL/DET/GRE), no mobile app, no
  community/social features yet. Focus on the IELTS coach MVP.
- Security debt: `backend/.env` contains real secrets and is tracked in git (rotate + untrack).
