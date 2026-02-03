#!/bin/sh
set -e

WORKDIR="${WORKDIR:-/project}"
COMPOSE_FILE="${COMPOSE_FILE:-$WORKDIR/docker-compose.yml}"
TIMEOUT="${TIMEOUT:-30}"
COUNT=0

cd "$WORKDIR"

echo "[dind] Waiting for Docker daemon..."
until docker info >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$TIMEOUT" ]; then
    echo "[dind] Timeout (${TIMEOUT}s). Docker daemon is not ready."
    exit 1
  fi
  sleep 1
done

echo "[dind] Docker daemon is ready."

echo "[dind] docker compose up using $COMPOSE_FILE ..."
docker compose -f "$COMPOSE_FILE" up -d
docker compose -f "$COMPOSE_FILE" ps
