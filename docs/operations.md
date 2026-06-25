# Testora — Operations Runbook

Operational procedures for running Testora in production. Pairs with the
deployment checklist in `README.md`.

## Environments

`APP_ENV` controls environment-specific safety. In `production` the API
**refuses to start on the mock grader** (`AI_PROVIDER=mock` or a real provider
with a missing key) — this prevents shipping fake grades. Set
`AI_PROVIDER=gemini` and a valid `GEMINI_API_KEY`.

## Health checks

| Endpoint        | Use                                   | Healthy response |
|-----------------|---------------------------------------|------------------|
| `/health/live`  | Liveness probe (process up)           | `200 {"status":"alive"}` |
| `/health/ready` | Readiness probe (DB + grader usable)  | `200 {"status":"ready"}` |
| `/health`       | Back-compat liveness alias            | `200 {"status":"ok"}` |

`/health/ready` returns `503` if the database is unreachable, or in production
if the effective grader resolved to mock. Wire load-balancer / k8s readiness to
`/health/ready` and liveness to `/health/live`.

## Database backups

State lives in PostgreSQL (`pgdata` volume). User audio lives in
`backend/private/audio_submissions` (not in the DB).

**Nightly logical backup (cron):**

```bash
pg_dump "$DATABASE_URL" --format=custom --file "/backups/testora_$(date +%F).dump"
# retain 14 days
find /backups -name 'testora_*.dump' -mtime +14 -delete
```

**Restore:**

```bash
pg_restore --clean --if-exists --dbname "$DATABASE_URL" /backups/testora_YYYY-MM-DD.dump
```

Test a restore into a scratch database at least monthly — an untested backup is
not a backup. Back up the audio directory separately (e.g. `rsync`/object store)
since it is not captured by `pg_dump`.

## Reading content import

The production Reading pack is authored in `backend/content/reading/test-01.json`
through `test-10.json`. Before importing into any persistent database, validate
the pack:

```bash
cd backend
python validate_reading.py
```

Expected result: 10 reading tests, 400 questions, and all checks passed. Import
is idempotent by title, so it is safe to repeat:

```bash
python import_content.py content/reading/test-*.json
```

Repeat the same import once after the first run; the second run should report
`added=0` and `skipped=10`. Legacy/demo Reading tests are intentionally hidden
from the public test catalogue unless their titles match
`IELTS Academic Reading - Test NN` or `IELTS Academic Reading — Test NN`.
Do not delete legacy tests directly if they have attempts attached; historical
attempts and review pages should remain available by id.

## Monitoring / metrics to watch

Logs are structured (`%(asctime)s %(levelname)s [%(name)s] %(message)s`). Key
loggers: `testora.ai.gemini`, `testora.writing`, `testora.speaking`.

| Signal                 | Where / how                                              | Alert when |
|------------------------|----------------------------------------------------------|------------|
| Grading failures       | `WARNING` from `testora.{writing,speaking}` ("saved as failed") | rate spikes |
| Gemini retries/errors  | `WARNING` from `testora.ai.gemini` (attempt N/3 failed)  | sustained retries |
| Auth failures / abuse  | `429` responses on `/auth/*`                             | sustained 429s |
| Readiness              | `/health/ready` non-200                                  | any in prod |
| Grading latency        | request duration on `/writing/submit`, `/speaking/submit`| p95 climbing |

Error tracking: set `SENTRY_DSN` (and `pip install sentry-sdk`) to report
unhandled exceptions; unset = disabled.

## Cost / abuse protection (current)

- Auth endpoints are IP rate-limited (10/min/IP, fixed window).
- Concurrent gradings are capped (`MAX_CONCURRENT_GRADINGS`, default 8) — bounds
  simultaneous Gemini calls (cost/quota) and threadpool usage.
- Inputs are bounded: writing `MAX_WRITING_CHARS` (20k), audio `MAX_AUDIO_UPLOAD_MB` (15).

Note: rate limiting is per-process; behind N workers the effective limit is
N×. For a hard global cap, move to a shared store (Redis) or enforce at the
proxy/CDN.

## Rollback procedure

1. **App code:** redeploy the previous image tag / git SHA. Containers are
   stateless, so this is immediate.
2. **Database migrations:** only roll back if the new release ran a migration
   that the old code can't tolerate. Each migration has a tested `downgrade()`:
   ```bash
   alembic downgrade -1
   ```
   Prefer forward-fixes over destructive downgrades when a migration dropped or
   rewrote data.
3. Confirm `/health/ready` is `200` and a smoke login + grade works.

## Incident response

1. **Detect** — alert fires (readiness down, grading-failure spike, 5xx surge).
2. **Triage** — check `/health/ready`; tail logs for the relevant `testora.*`
   logger; check Sentry for the top exception.
3. **Classify**
   - DB down → check Postgres / connectivity; `pool_pre_ping` auto-recovers
     transient drops.
   - Gemini failing → failures are saved as `failed` (no bogus grades) and users
     can re-submit; if sustained, check quota/key and consider a status notice.
   - Auth abuse → confirm 429s are doing their job; tighten proxy limits if needed.
4. **Mitigate** — roll back (above) if the incident correlates with a release.
5. **Recover & verify** — readiness green, error rate normal.
6. **Post-incident** — short write-up: timeline, root cause, follow-ups.
