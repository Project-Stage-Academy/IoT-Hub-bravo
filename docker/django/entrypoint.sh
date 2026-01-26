#!/bin/sh
set -e

# -----------------------------
# Wait for PostgreSQL with timeout
# -----------------------------
TIMEOUT=30 # seconds
COUNT=0

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$TIMEOUT" ]; then
    echo "Timeout ($TIMEOUT s). PostgreSQL is not ready."
    exit 1
  fi
  sleep 1
done

echo "PostgreSQL is ready!"

exec "$@"
