# OpenAPI developer guide

This guide is a practical, end-to-end workflow for maintaining the OpenAPI 3.0.3
spec in this repository.

## Navigation

- [Overview](#overview)
- [Repo structure](#repo-structure)
- [Requirements + permissions](#requirements--permissions)
- [Prerequisites & installation](#prerequisites--installation)
- [Typical workflow](#typical-workflow-copy-paste-commands)
- [Updating the spec](#updating-the-spec-practical-rules)
- [Linting / validating](#linting--validating)
- [Mock server](#mock-server)
- [Contract tests](#contract-tests-schemathesis)
- [Keeping spec and code in sync](#keeping-spec-and-code-in-sync)
- [Common failures / troubleshooting](#common-failures--troubleshooting)
- [Recommendations](#recommendations)
- [References](#references)

## Overview

The OpenAPI spec is used for:

- API documentation and examples.
- The local Prism mock server.
- Schemathesis contract tests.
- CI validation (lint + mock + contract tests).

## Repo structure

Spec and rules:

- OpenAPI spec: docs/api.yaml
- Spectral ruleset: docs/spectral.yaml

OpenAPI-related scripts in scripts/:

- scripts/lint-openapi.sh (Spectral lint)
- scripts/run-mock.sh (Prism mock server)
- scripts/run-api-tests.sh (Schemathesis contract tests)
- scripts/validate-openapi.sh (lint + mock + contract tests)

## Requirements + permissions

Prereqs used by the existing scripts:

- Node.js + npx (Prism & Spectral via npx)
- Python 3 + pip (Schemathesis CLI st)
- curl (used by validation script)

Make sure the scripts are executable (do this once):

```bash
chmod +x scripts/*.sh
```

## Prerequisites & installation

### Node.js and npx tools

npx is bundled with Node.js ≥ 16. Check if you have it:

```bash
node --version
npm --version
npx --version
```

If not installed:

**macOS (Homebrew)**:

```bash
brew install node
```

**Linux (Ubuntu/Debian)**:

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm
```

**Linux (Fedora/RHEL)**:

```bash
sudo dnf install -y nodejs npm
```

**Windows (Chocolatey)**:

```powershell
choco install nodejs
```

Alternatively, download from [nodejs.org](https://nodejs.org).

### Python 3 + Schemathesis

Check if you have Python 3:

```bash
python3 --version
pip3 --version
```

**Install Python**:

**macOS (Homebrew)**:

```bash
brew install python3
```

**Linux (Ubuntu/Debian)**:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip
```

**Linux (Fedora/RHEL)**:

```bash
sudo dnf install -y python3 python3-pip
```

**Windows (Chocolatey)**:

```powershell
choco install python
```

Alternatively, download from [python.org](https://www.python.org).

**Install Schemathesis (recommended: use a virtual environment)**:

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install Schemathesis:

```bash
pip install schemathesis
```

Verify installation:

```bash
st --version
```

### curl

curl is usually pre-installed on macOS and Linux.

**macOS**:

```bash
brew install curl
```

**Linux (Ubuntu/Debian)**:

```bash
sudo apt-get install -y curl
```

**Windows (Chocolatey)**:

```powershell
choco install curl
```

## Typical workflow (copy-paste commands)

Edit the spec:

```bash
docs/api.yaml
```

Run lint:

```bash
./scripts/lint-openapi.sh
```

Run the mock server:

```bash
./scripts/run-mock.sh
```

Run contract tests against the mock server:

```bash
./scripts/run-api-tests.sh
```

Run the full validation pipeline (lint + mock + contract tests):

```bash
./scripts/validate-openapi.sh
```

## Updating the spec (practical rules)

When you change backend routes, request/response shapes, or auth behavior, update
docs/api.yaml in the same PR.

Required fields per operation:

- `operationId` must be present and unique.
- `responses` must include every status code the backend can return.
- Each response must include the correct content types (for example,
	application/json).

Schemas:

- Define reusable models under components/schemas.
- Reference them via $ref (for example, $ref: "#/components/schemas/Device").
- Mark required fields explicitly and keep naming consistent with existing schema
	style.

Examples:

- Provide request and response examples for each operation.
- Update examples whenever schemas change to avoid stale docs.
- Keep examples small and realistic.

Backwards compatibility:

- Avoid breaking changes (removing fields, changing types, making optional fields
	required) unless the backend and clients are updated together.

## Linting / validating

Exact Spectral command used by the repo (from scripts/lint-openapi.sh):

```bash
npx @stoplight/spectral lint docs/api.yaml --ruleset docs/spectral.yaml --fail-severity error
```

Recommended script (same behavior):

```bash
./scripts/lint-openapi.sh
```

Linting catches syntax errors, style violations, missing required fields, and
inconsistent examples.

## Mock server

Run the mock server with the existing script:

```bash
./scripts/run-mock.sh
```

Defaults from the script:

- Host: 0.0.0.0
- Port: 4010
- Base URL: http://localhost:4010

Override host/port (supported by the script):

```bash
./scripts/run-mock.sh
```

Verify the mock server:

```bash
curl -s http://localhost:4010/health
```

## Contract tests (Schemathesis)

Contract tests run against the mock server and validate that example responses
conform to the OpenAPI spec.

What --phases examples means:

- Schemathesis only executes requests that have examples in the spec.
- This keeps tests deterministic and focused on documented behavior.

What is validated:

- Status Code Conformance: Response status codes must match those documented for each endpoint.
- Schema Conformance: Response bodies must strictly conform to the JSON schemas defined in components/schemas.
- Header Validation: Ensures all required headers are present and follow the defined format.

Use the existing script (preferred):

```bash
./scripts/run-api-tests.sh
```

This script runs the exact command below:

```bash
st run docs/api.yaml \
	--url http://localhost:4010 \
	--header "Authorization: Bearer your_test_jwt_token_here" \
	--phases examples \
	--exclude-checks unsupported_method \
	--force-color
```

Why --exclude-checks unsupported_method is used:

- Prism mock may not support every method declared in the spec, and this avoids
	false failures for unsupported methods during mock-based testing.


## Keeping spec and code in sync

- Any backend change must update docs/api.yaml in the same PR.
- CI runs lint + contract tests and blocks merges on failures
	(.github/workflows/lint-and-tests-api.yml runs scripts/validate-openapi.sh).
- Always update examples when schemas change.

## Common failures / troubleshooting

1) Spectral lint errors for missing `operationId`
	 - Fix: add a unique `operationId` to each operation.

2) Lint failures for missing response content types
	 - Fix: ensure each response has a content section with the correct media type
		 (for example, application/json).

3) Mock server fails to start (script not executable)
	 - Fix: run chmod +x scripts/*.sh.

4) Schemathesis command not found (st)
	 - Fix: install Schemathesis in your environment or run
		 scripts/validate-openapi.sh which checks prerequisites.

5) Contract tests fail due to response schema mismatch
	 - Fix: update response schemas or example payloads to match actual responses.

6) Mock server not reachable
	 - Fix: verify host/port (defaults to http://localhost:4010) and ensure
		 scripts/run-mock.sh is running.
## Recommendations

- **Use the validation script before pushing**: `./scripts/validate-openapi.sh` runs
  all checks (lint, mock, contract tests) in one command.
- **Keep examples in sync**: Every schema change should include updated examples.
  Outdated examples cause contract test failures.
- **Check CI logs early**: If lint/contract tests fail in CI, review the full
  scripts/validate-openapi.sh output locally to debug faster.
- **Test with real tokens**: Contract tests run against the mock server, but
  consider testing live endpoints separately with a real token.
- **Document design decisions**: If adding complex endpoints, document the
  rationale in comments within the spec.
- **Use operationId consistently**: Use a pattern like `list_devices`, `get_device`,
  `create_device` for SDK generation and internal consistency.
- **Version the spec**: Consider tagging the spec version in the OpenAPI info
  field whenever you make breaking changes.

