#!/usr/bin/env bash
set -e
set -o nounset

NAME="${NAME:-iot-hub-dind}"

docker rm -f "$NAME" >/dev/null 2>&1 || true

echo "[host] removed: $NAME"
