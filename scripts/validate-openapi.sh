#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status,
# treat unset variables as an error, and propagate errors in pipelines
set -euo pipefail

# ==============================
# Configuration
# ==============================
MOCK_PORT=${MOCK_PORT:-4010}
MOCK_HOST=${MOCK_HOST:-"0.0.0.0"}
MOCK_URL="http://${MOCK_HOST}:${MOCK_PORT}"
SPEC_FILE=${SPEC_FILE:-"docs/api.yaml"}
LOG_DIR="logs"
PRISM_LOG="${LOG_DIR}/prism.log"

# Check if required commands exist
check_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: Required command '$1' is not installed. Aborting."
    exit 1
  }
}

# Ensure a script is executable
check_executable() {
  if [ ! -x "$1" ]; then
    echo "Making $1 executable..."
    chmod +x "$1"
  fi
}

# ==============================
# Pre-checks
# ==============================
echo "==> Checking required commands..."
check_command npx
check_command curl
check_command python3
check_command pip

# Ensure helper scripts are executable
check_executable ./scripts/lint-openapi.sh
check_executable ./scripts/run-api-tests.sh

# Create log directory if not exists
mkdir -p "${LOG_DIR}"

# ==============================
# Step 1: Lint OpenAPI specification
# ==============================
echo "==> 1) Lint OpenAPI spec with Spectral..."
./scripts/lint-openapi.sh

# ==============================
# Step 2: Start Prism mock server
# ==============================
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

# Cleanup function to stop Prism when script exits
cleanup() {
  echo "==> Stopping Prism (PID ${PRISM_PID})..."
  kill "${PRISM_PID}" 2>/dev/null || true
}
trap cleanup EXIT

# Wait until Prism is ready
echo "==> 3) Waiting for Prism to become ready..."
for i in {1..30}; do
  if curl -s "${MOCK_URL}/health" >/dev/null 2>&1; then
    echo "    Prism is up at ${MOCK_URL}"
    break
  fi

  sleep 0.5
done


# ==============================
# Step 3: Run Schemathesis contract tests
# ==============================
echo -e "\n Running Schemathesis Contract Tests..."
./scripts/run-api-tests.sh

echo -e "\n✨ SUCCESS: API contract is valid!"
