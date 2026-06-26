#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 path/to/testora_db_YYYYmmddTHHMMSSZ.dump [path/to/testora_audio_YYYYmmddTHHMMSSZ.tgz]" >&2
  exit 2
fi

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DB_FILE="$1"
AUDIO_FILE="${2:-}"

cat "$DB_FILE" | docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_restore --clean --if-exists -U postgres -d testora

if [ -n "$AUDIO_FILE" ]; then
  cat "$AUDIO_FILE" | docker compose -f "$COMPOSE_FILE" exec -T backend \
    sh -c "mkdir -p /app/private/audio_submissions && cd /app/private/audio_submissions && tar -xzf -"
fi

echo "Restore complete."
