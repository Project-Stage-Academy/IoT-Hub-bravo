#!/usr/bin/env bash
set -euo pipefail

MOCK_PORT=${MOCK_PORT:-4010}
MOCK_HOST=${MOCK_HOST:-"0.0.0.0"}
MOCK_URL="http://${MOCK_HOST}:${MOCK_PORT}"
SPEC_FILE=${SPEC_FILE:-"docs/api.yaml"}
LOG_DIR="logs"
PRISM_LOG="${LOG_DIR}/prism.log"

mkdir -p "${LOG_DIR}"

echo "==> 1) Lint OpenAPI spec with Spectral..."
./scripts/lint-openapi.sh

echo "==> 2) Starting Prism mock server..."
npx @stoplight/prism-cli mock "${SPEC_FILE}" \
  --port "${MOCK_PORT}" \
  --host "${MOCK_HOST}" \
  --dynamic \
  --errors \
  > "${PRISM_LOG}" 2>&1 &

PRISM_PID=$!
echo "    Prism PID: ${PRISM_PID}"
echo "    Logs: ${PRISM_LOG}"

cleanup() {
  echo "==> Stopping Prism (PID ${PRISM_PID})..."
  kill "${PRISM_PID}" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> 3) Waiting for Prism to become ready..."
for i in {1..30}; do
  if curl -s "${MOCK_URL}/health" >/dev/null 2>&1; then
    echo "    Prism is up at ${MOCK_URL}"
    break
  fi

  sleep 0.5
done

echo -e "\n Running Schemathesis Contract Tests..."
./scripts/run-api-tests.sh

echo -e "\n✨ SUCCESS: API contract is valid!"
