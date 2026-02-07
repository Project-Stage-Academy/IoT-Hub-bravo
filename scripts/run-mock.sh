#!/usr/bin/env bash

# =============================================================================
#   Local Mock Server using Prism for OpenAPI specification
# =============================================================================

# ────────────────────────────────────────────────
# Configuration (change here if needed)

SPEC_FILE=${SPEC_FILE:-"docs/api.yaml"}           # path to your OpenAPI file
PORT=${MOCK_PORT:-4010}                           # port (can be overridden: MOCK_PORT=8080 ./run-mock.sh)
HOST=${MOCK_HOST:-"0.0.0.0"}                      # 0.0.0.0 allows access from the local network

# ────────────────────────────────────────────────

# Check if the spec file exists
if [[ ! -f "$SPEC_FILE" ]]; then
  echo "Error: specification file not found"
  echo "  Path: $SPEC_FILE"
  echo "Please check the file name or path in the script."
  exit 1
fi

# Check if npx is available
if ! command -v npx &> /dev/null; then
  echo "Error: npx not found."
  echo "Please install Node.js[](https://nodejs.org)"
  exit 1
fi

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
