#!/usr/bin/env bash
# Back up the Testora Postgres database (Neon or any Postgres) with pg_dump.
#
#   DATABASE_URL=postgresql://... bash scripts/backup_prod.sh
#
# Writes backups/testora_db_<UTC timestamp>.dump.gz (custom format, mode 600) and
# prunes files older than RETENTION_DAYS. The connection string is read from the
# environment only and is never printed.
#
# Env: DATABASE_URL (required), BACKUP_DIR (default: backups), RETENTION_DAYS (default: 14)
set -euo pipefail

: "${DATABASE_URL:?set DATABASE_URL (postgresql://...)}"
command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump not found (install postgresql-client, same major version as the server)" >&2; exit 1; }

BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/testora_db_$STAMP.dump.gz"

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

# Connection settings go through PG* environment variables, not argv.
if pg_env_from_url "$DATABASE_URL"; then
  CONN=()
else
  CONN=(--dbname="$DATABASE_URL")
fi

umask 077
mkdir -p "$BACKUP_DIR"

# --no-owner/--no-privileges make the dump restorable into a different role
# setup (e.g. a fresh Neon branch). Dump first, compress after, so a pg_dump
# failure is never hidden by a successful gzip in a pipe.
if ! pg_dump ${CONN[@]+"${CONN[@]}"} --format=custom --no-owner --no-privileges --file="$OUT.raw" 2>"$OUT.err"; then
  # pg_dump errors can echo the host; show them but never the password.
  sed 's|://[^@/ ]*@|://***@|g' "$OUT.err" >&2
  rm -f "$OUT.raw" "$OUT.err"
  echo "pg_dump failed; no backup written" >&2
  exit 1
fi
rm -f "$OUT.err"
gzip -1 -c "$OUT.raw" > "$OUT.tmp"
rm -f "$OUT.raw"
mv "$OUT.tmp" "$OUT"
chmod 600 "$OUT"

find "$BACKUP_DIR" -name "testora_db_*.dump.gz" -mtime "+$RETENTION_DAYS" -delete

printf "Backup written: %s (%s)\n" "$OUT" "$(wc -c < "$OUT" | tr -d ' ') bytes"
