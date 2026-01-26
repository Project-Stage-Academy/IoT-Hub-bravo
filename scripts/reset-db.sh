#!/usr/bin/env bash
set -e

PROJECT_RAW="$(basename "$(pwd)")"
PROJECT="$(echo "$PROJECT_RAW" | tr '[:upper:]' '[:lower:]')"
DB_VOLUME="${PROJECT}_db_data"

echo "[reset-db] stopping containers..."
docker compose down

echo "[reset-db] removing db volume..."
docker volume rm "$DB_VOLUME"

echo "[reset-db] starting containers..."
docker compose up -d

docker compose ps
echo "[reset-db] done."
