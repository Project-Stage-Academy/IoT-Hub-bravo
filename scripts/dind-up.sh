#!/usr/bin/env bash
set -e

NAME="${NAME:-iot-hub-dind}"
WORKDIR="${WORKDIR:-/project}"

cleanup_on_error() {
  echo "[host] ERROR: cleaning up dind container..."
  docker logs "$NAME" --tail=200 >/dev/null 2>&1 || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}

trap cleanup_on_error ERR

# remove old dind container if exists
docker rm -f "$NAME" >/dev/null 2>&1 || true

echo "[host] starting dind container: $NAME"
docker run -d \
  --name "$NAME" \
  --privileged \
  -v "$(pwd)":"$WORKDIR" \
  -w "$WORKDIR" \
  -p 8000:8000 \
  -p 5555:5555 \
  docker:27-dind

# check that container exists and is running
if [[ "$(docker inspect -f '{{.State.Running}}' "$NAME")" != "true" ]]; then
  echo "[host] ERROR: dind container is not running"
  false
fi

echo "[host] dind container is running"
echo "[host] running demo script inside dind container..."

docker exec -w "$WORKDIR" "$NAME" sh ./docker/dind/demo.sh

trap - ERR
echo "[host] done."
