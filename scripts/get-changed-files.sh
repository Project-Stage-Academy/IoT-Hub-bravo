#!/bin/bash
# Script to get changed Python files in a PR
# Usage: ./scripts/get-changed-files.sh [base-branch]

set -e

BASE_BRANCH="${1:-origin/main}"

echo "Fetching changes from base branch: $BASE_BRANCH" >&2

# Get list of changed Python files
git diff --name-only --diff-filter=ACMRT "$BASE_BRANCH"...HEAD | grep '\.py$' || true
