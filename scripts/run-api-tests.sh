#!/usr/bin/env bash

set -euo pipefail

SPEC_FILE=${SPEC_FILE:-"docs/api.yaml"}
BASE_URL="http://localhost:${MOCK_PORT:-4010}"
TOKEN=${API_TEST_TOKEN:-"your_test_jwt_token_here"}

echo "🚀 Starting Lightweight Contract Tests..."

if ! command -v st &> /dev/null; then
  echo "❌ Error: Schemathesis (st) is not installed."
  exit 1
fi

st run "$SPEC_FILE" \
  --url "$BASE_URL" \
  --header "Authorization: Bearer $TOKEN" \
  --phases examples \
  --checks all \
  --exclude-checks unsupported_method \
  --force-color