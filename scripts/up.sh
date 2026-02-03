#!/usr/bin/env bash
set -e

echo "[up] starting containers..."
docker compose up -d --build

echo "[up] status:"
docker compose ps

echo " - App: http://localhost:8000/"
echo " - Admin: http://localhost:8000/admin/"
echo " - Swagger UI: http://localhost:5433/"
echo " - Flower: http://localhost:5555/"
echo "[up] done."
