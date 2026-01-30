#!/bin/sh
set -e

# =============================
# Configuration
# =============================
TIMEOUT="${TIMEOUT:-30}" # seconds

# =============================
# Helpers
# =============================
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

wait_for_service () {
  # $1 - service name
  # $2.. - command to run (success when exit code == 0)
  SERVICE="$1"
  shift

  log "Waiting for ${SERVICE} with timeout $TIMEOUT seconds..."
  COUNT=0

  until "$@" >/dev/null 2>&1; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$TIMEOUT" ]; then
      log "Timeout (${TIMEOUT}s). ${SERVICE} is not ready."
      exit 1
    fi
    sleep 1
  done

  log "${SERVICE} is ready!"
}

# -----------------------------
# Wait for PostgreSQL
# -----------------------------
wait_for_service \
  "PostgreSQL at ${DB_HOST}:${DB_PORT}" \
  pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"

# -----------------------------
# Wait for Redis
# -----------------------------
wait_for_service \
  "Redis at ${REDIS_HOST}:${REDIS_PORT:-6379}" \
  redis-cli -h "$REDIS_HOST" -p "${REDIS_PORT:-6379}" ping

# =============================
# Start main process
# =============================
exec "$@"
