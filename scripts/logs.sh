#!/usr/bin/env bash
set -e

SERVICE="${1:-}"

if [ -n "$SERVICE" ]; then
  echo "[logs] of: $SERVICE"
  docker compose logs -f --tail=200 "$SERVICE"
else
  echo "[logs] of: all services"
  docker compose logs -f --tail=200
fi
