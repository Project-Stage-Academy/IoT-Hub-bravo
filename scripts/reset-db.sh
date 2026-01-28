#!/usr/bin/env bash
set -e

PROJECT_NAME="$(echo "${COMPOSE_PROJECT_NAME:-iot-hub}" | tr '[:upper:]' '[:lower:]')"
DB_VOLUME="${PROJECT_NAME}_db_data"

echo "[reset-db] compose project: ${PROJECT_NAME}"
echo "[reset-db] db volume: ${DB_VOLUME}"

# check if the volume exists
if ! docker volume inspect "$DB_VOLUME" >/dev/null 2>&1; then
  echo "[reset-db] db volume not found: $DB_VOLUME"
  exit 1
fi

# get confirmation from user
echo "[reset-db] ABOUT TO DELETE volume: $DB_VOLUME. Type 'YES' to confirm:"
read -r CONFIRM

if [[ "$CONFIRM" != "YES" ]]; then
  echo "[reset-db] cancelled."
  exit 1
fi

echo "[reset-db] stopping containers..."
docker compose down

echo "[reset-db] removing db volume..."
docker volume rm "$DB_VOLUME"

echo "[reset-db] starting containers..."
docker compose up -d

docker compose ps
echo "[reset-db] done."
