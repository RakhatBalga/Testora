# Testora frontend

Next.js 16 (App Router) + TypeScript + Tailwind v4 client for the Testora IELTS practice platform. It talks to the FastAPI backend in `../backend` through a single network layer (`src/shared/api`).

## Run

```bash
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at the backend
npm ci
npm run dev                  # http://localhost:3000
```

| Script | Purpose |
|---|---|
| `npm run lint` | ESLint (includes the FSD import-boundary rules) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run test:run` | Vitest (jsdom) |
| `npm run build` | Production build |

`NEXT_PUBLIC_*` variables are inlined at build time. `NEXT_PUBLIC_API_URL` is also the API origin allowed by the CSP in `next.config.ts`.

## Layout (Feature-Sliced Design)

```
src/
  app/        routes only: composition, metadata, no business logic
  widgets/    large page blocks (app shell, landing, dashboard)
  features/   user-facing capabilities (auth, reading/listening sessions, feedback, ...)
  entities/   domain models and UI (test, dashboard, coach)
  shared/     api client, auth, lib helpers, ui kit, config
```

Imports go downwards only (`app` -> `widgets` -> `features` -> `entities` -> `shared`), and each slice is imported through its `index.ts` barrel. ESLint enforces both rules.

## Notes

- The session token lives in `sessionStorage` (per tab).
- The backend sleeps on the free Render tier: `shared/api` applies a request timeout, retries idempotent GETs and pings `/health/live` on the landing and login pages.
- Exam timers are deadline-based (`shared/lib/useExamTimer`), so background tabs cannot stretch the clock.
