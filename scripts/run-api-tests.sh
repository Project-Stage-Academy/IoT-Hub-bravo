#!/usr/bin/env bash
# =============================================================================
# Run Lightweight API Contract Tests using Schemathesis
# =============================================================================

set -euo pipefail # Exit on error, treat unset variables as error, propagate errors in pipelines

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
SPEC_FILE=${SPEC_FILE:-"docs/api.yaml"}                 # Path to OpenAPI specification   
BASE_URL="http://localhost:${MOCK_PORT:-4010}"          # Base URL for mock server
TOKEN=${API_TEST_TOKEN:-"your_test_jwt_token_here"}     # Authorization token for API tests

# Check if a command exists
check_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: Required command '$1' is not installed. Please install it before running this script."
    exit 1
  }
}

echo "Starting Lightweight Contract Tests..."

# Check that Schemathesis CLI is installed
check_command st

# Ensure spec file exists
if [[ ! -f "$SPEC_FILE" ]]; then
  echo "Error: OpenAPI specification file not found at $SPEC_FILE"
  exit 1
fi

# Ensure spec file exists
if [[ ! -f "$SPEC_FILE" ]]; then
  echo "Error: OpenAPI specification file not found at $SPEC_FILE"
  exit 1
fi

# ────────────────────────────────────────────────
# Run Schemathesis Tests
# ────────────────────────────────────────────────
echo "Running Schemathesis contract tests against $BASE_URL"
st run "$SPEC_FILE" \
  --url "$BASE_URL" \
  --header "Authorization: Bearer $TOKEN" \
  --phases examples \
  --checks all \
  --exclude-checks unsupported_method \
  --force-color

echo "Schemathesis contract tests completed successfully!"