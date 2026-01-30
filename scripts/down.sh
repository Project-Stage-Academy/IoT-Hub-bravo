#!/usr/bin/env bash
set -e

echo "[down] stopping containers..."
docker compose down --remove-orphans

echo "[down] done."
