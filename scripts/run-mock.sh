#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status,
# treat unset variables as an error, and propagate errors in pipelines
set -euo pipefail  

# =============================================================================
#   Local Mock Server using Prism for OpenAPI specification
# =============================================================================


# ────────────────────────────────────────────────
# Configuration (change here if needed)

SPEC_FILE=${SPEC_FILE:-"docs/api.yaml"}           # path to your OpenAPI file
PORT=${MOCK_PORT:-4010}                           # port (can be overridden: MOCK_PORT=8080 ./run-mock.sh)
HOST=${MOCK_HOST:-"0.0.0.0"}                      # 0.0.0.0 allows access from the local network

# ────────────────────────────────────────────────

# Check if a command exists
check_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: Required command '$1' is not installed. Please install it before running this script."
    exit 1
  }
}

# Ensure spec file exists
if [[ ! -f "$SPEC_FILE" ]]; then
  echo "ERROR: OpenAPI specification file not found"
  echo "  Path: $SPEC_FILE"
  echo "Please check the path or file name."
  exit 1
fi

# Ensure Node.js/npm is installed
check_command node
check_command npx

# ────────────────────────────────────────────────
# Start Mock Server
# ────────────────────────────────────────────────
echo ""
echo "Starting mock server (Prism)"
echo "  Spec file:   $SPEC_FILE"
echo "  Address:     http://localhost:$PORT"
echo "  Mode:        dynamic responses (faker)"
echo ""
echo "To stop → press Ctrl + C"
echo ""

# Launch the mock server
npx @stoplight/prism-cli mock "$SPEC_FILE" \
  --port "$PORT" \
  --host "$HOST" \
  --dynamic \
  --errors
