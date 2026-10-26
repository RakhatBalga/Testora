#!/bin/sh
set -eu

alembic upgrade head

# Behind Render's proxy the real client IP arrives in X-Forwarded-For. The app
# derives it itself, trusting the header only from TRUSTED_PROXY_CIDRS, so keep
# uvicorn's own rewrite limited to loopback unless FORWARDED_ALLOW_IPS says otherwise.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}" \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
