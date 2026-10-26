#!/usr/bin/env sh
# Back up the Testora Postgres database (Neon or any Postgres) with pg_dump.
#
#   DATABASE_URL=postgresql://... scripts/backup_prod.sh
#
# Writes backups/testora_db_<UTC timestamp>.dump.gz (custom format, mode 600) and
# prunes files older than RETENTION_DAYS. The connection string is read from the
# environment only and is never printed.
#
# Env: DATABASE_URL (required), BACKUP_DIR (default: backups), RETENTION_DAYS (default: 14)
set -eu

: "${DATABASE_URL:?set DATABASE_URL (postgresql://...)}"
command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump not found (install postgresql-client, same major version as the server)" >&2; exit 1; }

BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/testora_db_$STAMP.dump.gz"

umask 077
mkdir -p "$BACKUP_DIR"

# --no-owner/--no-privileges make the dump restorable into a different role
# setup (e.g. a fresh Neon branch). Dump first, compress after, so a pg_dump
# failure is never hidden by a successful gzip in a pipe.
if ! pg_dump --dbname="$DATABASE_URL" --format=custom --no-owner --no-privileges --file="$OUT.raw" 2>"$OUT.err"; then
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
