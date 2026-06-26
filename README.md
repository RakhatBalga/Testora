# Testora — AI IELTS Coach

Grade → extract mistakes → name the band blocker → tell the user what to do
today → re-grade → show the band move. FastAPI + PostgreSQL backend, Next.js
frontend, Gemini grading, with a local-only mock fallback for development.

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
- [ ] `NEXT_PUBLIC_API_URL` points at the public API origin
- [ ] `APP_ENV=production`
- [ ] `AI_PROVIDER=gemini` **and** `GEMINI_API_KEY` set (the API refuses to start
      in production if grading would fall back to mock)
- [ ] Reading pack imported and validated: `cd backend && python validate_reading.py`
- [ ] DB backups configured for the `pgdata` volume

## Operational notes
- **Rate limiting** is in-process (per backend worker). Behind multiple workers
  or replicas the effective limit scales with worker count; use a shared store
  (Redis) or proxy-level limiting if you need a hard global cap.
- **Recordings** are stored privately under `backend/private/audio_submissions`
  and served only to their owner via an authenticated endpoint.
- **Failed AI grades** are saved without a band (Writing `status="failed"`) and
  excluded from analytics — never as a Band 0.

## Tests

Backend:
```bash
cd backend
python validate_reading.py
python scripts/check_migration_heads.py
pytest
```

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
