#!/usr/bin/env bash
set -euo pipefail

SPEC_FILE="docs/api.yaml"
RULESET_FILE="docs/spectral.yaml"

echo "==> Running Spectral OpenAPI lint..."
npx @stoplight/spectral lint "${SPEC_FILE}" --ruleset "${RULESET_FILE}" --fail-severity error
