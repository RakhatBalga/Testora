#!/usr/bin/env bash
# Restore a backup made by backup_prod.sh into the database in DATABASE_URL.
#
#   DATABASE_URL=postgresql://<target> bash scripts/restore_prod.sh FILE.dump.gz --yes
#
# DESTRUCTIVE: existing objects are dropped (--clean --if-exists) before being
# recreated. Requires --yes. If the target looks like production (APP_ENV=production,
# the host contains neon.tech, or PROD_DB_HOST_MARKER is a substring of the URL) it also requires --target-is-prod.
# Prefer restoring into a new Neon branch or a scratch database first.
# The dump is verified (gzip -t, pg_restore --list) before the database is touched,
# and applied in a single transaction that stops at the first error.
# The connection string is never printed or passed on the command line.
set -euo pipefail

FILE=""
YES=0
PROD=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --target-is-prod) PROD=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
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

# Split a postgres:// URL into libpq PG* variables so the password never
# appears in a process argument list. Falls back to the URL itself (empty
# result) for shapes this simple parser does not handle, such as IPv6 hosts.
pg_env_from_url() {
  local url="$1" rest query="" auth db="" cred hostport user pass="" host port="" kv
  rest="${url#*://}"
  if [[ "$rest" == *\?* ]]; then query="${rest#*\?}"; rest="${rest%%\?*}"; fi
  auth="${rest%%/*}"
  [[ "$rest" == */* ]] && db="${rest#*/}"
  if [[ "$auth" == *@* ]]; then
    cred="${auth%@*}"; hostport="${auth##*@}"
    user="${cred%%:*}"
    [[ "$cred" == *:* ]] && pass="${cred#*:}"
  else
    return 1
  fi
  [[ "$hostport" == \[* ]] && return 1
  host="${hostport%%:*}"
  [[ "$hostport" == *:* ]] && port="${hostport##*:}"
  [[ -n "$host" && -n "$user" && -n "$db" ]] || return 1
  urldecode() { local s="${1//+/ }"; printf '%b' "${s//%/\\x}"; }
  export PGHOST="$host" PGUSER="$(urldecode "$user")" PGDATABASE="$(urldecode "$db")"
  [[ -n "$port" ]] && export PGPORT="$port"
  [[ -n "$pass" ]] && export PGPASSWORD="$(urldecode "$pass")"
  local IFS='&'
  for kv in $query; do
    case "$kv" in
      sslmode=*) export PGSSLMODE="${kv#*=}" ;;
      channel_binding=*) export PGCHANNELBINDING="${kv#*=}" ;;
      options=*) export PGOPTIONS="$(urldecode "${kv#*=}")" ;;
    esac
  done
  return 0
}

# Decompress to a private temp file so the dump can be checked before any
# change, and so a failing decompress is not hidden inside a pipe.
umask 077
TMP="$(mktemp "${TMPDIR:-/tmp}/testora_restore.XXXXXX")"
trap 'rm -f "$TMP"' EXIT
case "$FILE" in
  *.gz)
    gzip -t "$FILE" || { echo "Backup is corrupt (gzip -t failed); nothing was changed." >&2; exit 1; }
    gzip -dc "$FILE" > "$TMP"
    ;;
  *) cat "$FILE" > "$TMP" ;;
esac
chmod 600 "$TMP"
pg_restore --list "$TMP" > /dev/null || { echo "Not a valid pg_dump custom-format archive; nothing was changed." >&2; exit 1; }

if pg_env_from_url "$DATABASE_URL"; then
  CONN=()
else
  CONN=(--dbname="$DATABASE_URL")
fi

pg_restore --clean --if-exists --no-owner --no-privileges \
  --single-transaction --exit-on-error ${CONN[@]+"${CONN[@]}"} "$TMP"

echo "Restore complete."
