#!/usr/bin/env bash
set -e

NAME="${NAME:-iot-hub-dind}"
WORKDIR="${WORKDIR:-/project}"

docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$NAME" \
  --privileged \
  -v "$(pwd)":"$WORKDIR" \
  -w "$WORKDIR" \
  -p 8000:8000 \
  -p 5555:5555 \
  docker:27-dind

docker exec -w "$WORKDIR" "$NAME" sh ./docker/dind/demo.sh
