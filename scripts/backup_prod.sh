#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"

DB_FILE="$BACKUP_DIR/testora_db_$STAMP.dump"
AUDIO_FILE="$BACKUP_DIR/testora_audio_$STAMP.tgz"

docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U postgres -d testora --format=custom > "$DB_FILE"

docker compose -f "$COMPOSE_FILE" exec -T backend \
  sh -c "cd /app/private/audio_submissions && tar -czf - ." > "$AUDIO_FILE"

find "$BACKUP_DIR" -name "testora_db_*.dump" -mtime "+$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "testora_audio_*.tgz" -mtime "+$RETENTION_DAYS" -delete

printf "Backup written:\n  %s\n  %s\n" "$DB_FILE" "$AUDIO_FILE"
