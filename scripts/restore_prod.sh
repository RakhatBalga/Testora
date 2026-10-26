#!/usr/bin/env sh
# Restore a backup made by backup_prod.sh into the database in DATABASE_URL.
#
#   DATABASE_URL=postgresql://<target> scripts/restore_prod.sh FILE.dump.gz --yes
#
# DESTRUCTIVE: existing objects are dropped (--clean --if-exists) before being
# recreated. Requires --yes. If the target looks like production (APP_ENV=production,
# the host contains neon.tech, or PROD_DB_HOST_MARKER is a substring of the URL) it also requires --target-is-prod.
# Prefer restoring into a new Neon branch or a scratch database first.
# The connection string is never printed.
set -eu

FILE=""
YES=0
PROD=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --target-is-prod) PROD=1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    -*) echo "Unknown option: $arg" >&2; exit 2 ;;
    *) FILE="$arg" ;;
  esac
done

[ -n "$FILE" ] || { echo "Usage: DATABASE_URL=... $0 FILE.dump.gz --yes [--target-is-prod]" >&2; exit 2; }
[ -f "$FILE" ] || { echo "Backup file not found: $FILE" >&2; exit 2; }
: "${DATABASE_URL:?set DATABASE_URL to the TARGET database}"
[ "$YES" -eq 1 ] || { echo "Refusing to restore without --yes (this overwrites the target database)." >&2; exit 2; }
command -v pg_restore >/dev/null 2>&1 || { echo "pg_restore not found (install postgresql-client)" >&2; exit 1; }

IS_PROD=0
[ "${APP_ENV:-}" = "production" ] && IS_PROD=1
# Any Neon host is treated as production-like (Testora prod lives on Neon).
case "$DATABASE_URL" in *neon.tech*) IS_PROD=1 ;; esac
if [ -n "${PROD_DB_HOST_MARKER:-}" ]; then
  case "$DATABASE_URL" in *"$PROD_DB_HOST_MARKER"*) IS_PROD=1 ;; esac
fi
if [ "$IS_PROD" -eq 1 ] && [ "$PROD" -ne 1 ]; then
  echo "Target looks like production. Re-run with --target-is-prod if you really mean it." >&2
  exit 2
fi

case "$FILE" in
  *.gz) gzip -dc "$FILE" ;;
  *) cat "$FILE" ;;
esac | pg_restore --clean --if-exists --no-owner --no-privileges --dbname="$DATABASE_URL"

echo "Restore complete."
