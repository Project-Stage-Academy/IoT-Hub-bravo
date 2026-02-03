# CI Pipeline (GitHub Actions)

This repository uses GitHub Actions to enforce basic quality gates on pull requests.
The pipeline provides fast feedback and blocks merges when core checks fail.

Workflow file: `.github/workflows/ci.yml`  
Workflow name: **CI on Pull Request**

## When it runs

The CI workflow runs on:

- **Pull requests to `main`** (quality gate for merging)
- **Manual runs** with `workflow_dispatch` (Actions → Run workflow)

## Jobs and ordering

The pipeline is split into four jobs with strict ordering:

1. `lint` + `security-scan` (parallel) → 2. `test` → 3. `build`

The dependency chain is enforced with `needs`:

- `test` runs only if both `lint` and `security-scan` complete
- `build` runs only if `test` succeeds

### 1) Lint job

- Runs on: `ubuntu-22.04`
- Python: `3.11`
- Working directory: `backend/`

Purpose:

- Enforce consistent formatting and catch basic code issues.

Tools:

- `black==24.10.0`
- `ruff==0.12.0`

Checks:

- `black --check .` — verifies code formatting without modifying files
- `ruff check .` — runs static lint rules and fails on violations

Expected outcome:

- Any formatting or lint violations fail the job and block the pipeline.

### 2) Security Scan job

- Runs on: `ubuntu-22.04`
- Python: `3.11`
- Working directory: `backend/`

Purpose:

- Scan Python dependencies for known security vulnerabilities.

Tool:

- `safety` — checks `requirements.txt` against SafetyDB vulnerability database

Execution:

- `safety check --file requirements.txt` — scans all dependencies
- Job uses `continue-on-error: true` to not block pipeline on warnings
- Security report is uploaded as artifact for review

Expected outcome:

- Vulnerabilities are reported in job logs
- Job completes successfully even if vulnerabilities are found (non-blocking)
- Team should review findings and update dependencies as needed

**Note**: For production deployments, consider making this job blocking or adding severity thresholds.

### 3) Test job

- Runs on: `ubuntu-22.04`
- Python matrix: `3.10`, `3.11`

Purpose:

- Execute unit tests (placeholder suite initially)
- Produce a test coverage report (`coverage.xml`) and upload it as an artifact

#### Database service (TimescaleDB / PostgreSQL 16)

The test job starts a DB service container:

- Image: `timescale/timescaledb:latest-pg16`
- Service name: `db` (reachable as hostname `db` inside the job)

Environment used by the application/tests:

- `DB_NAME=testdb`
- `DB_USER=postgres`
- `DB_PASSWORD=testpassword`
- `DB_HOST=db`
- `DB_PORT=5432`

Healthcheck is configured using `pg_isready` so that job waits until the DB container reports healthy.

#### Test execution

- Dependencies are installed from `backend/requirements.txt`
- Tests are executed with coverage:

`pytest -q --cov=. --cov-report=xml:coverage.xml`

#### Artifacts

Each Python version uploads a separate artifact:

- `coverage-3.10` → `backend/coverage.xml`
- `coverage-3.11` → `backend/coverage.xml`

You can download artifacts from:
Actions → select a workflow run → **Artifacts**.

### 4) Build job

- Runs on: `ubuntu-22.04`
- Build context: repository root
- Dockerfile: `./docker/django/Dockerfile`

Build toolchain:

- `docker/setup-buildx-action`
- `docker/build-push-action`

Purpose:

- Smoke-build the Django Docker image (no push)
- Ensure the `Dockerfile` remains buildable in CI

### Dependency caching

Python dependencies are cached by `actions/setup-python` with:

- `cache`: `pip`
- `cache-dependency-path`: `backend/requirements.txt`

This caches pip downloads/wheels to speed up subsequent runs.

Docker builds use `Buildx` cache stored in GitHub Actions cache via:

- `cache-from`: `type=gha`
- `cache-to`: `type=gha,mode=max`

## Running the same checks locally

All commands below are run from the repository root unless stated otherwise.

### 1) Lint locally

```bash
cd backend
python -m pip install -U pip
python -m pip install black==24.10.0 ruff==0.12.0

black --check .
ruff check .
```

If you want auto-formatting (instead of check-only):

```bash
black .
```

### 2) Test locally

- Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
- Configure environment file according to instructions in [README.md](../README.md).

- Start development environment (For more details, see [docs/dev-environment.md](../docs/dev-environment.md)):
  ```bash
  docker compose up -d --build
  ```

- Run tests:
  ```bash
  docker compose run --rm web pytest -q --cov=. --cov-report=xml:coverage.xml
  ```

### 3) Run security scan locally

```bash
cd backend
python -m pip install safety
safety check --file requirements.txt
```

For JSON output:

```bash
safety check --file requirements.txt --json
```

### 4) Build Docker image locally

```bash
docker build -f ./docker/django/Dockerfile -t iot-hub/django:local .
```

## Vulnerability Scanning and Triage

The CI pipeline includes automated vulnerability scanning using `safety` to check Python dependencies against known security vulnerabilities.

### How It Works

1. **Automated Scanning**: The `security-scan` job runs on every pull request
2. **Non-Blocking**: Currently configured to not block the pipeline (`continue-on-error: true`)
3. **Reporting**: Findings are displayed in job logs and uploaded as artifacts

### Triage Process

When vulnerabilities are detected:

#### 1. Assess Severity

Review the safety output to identify:
- **CVE ID**: Unique identifier for the vulnerability
- **Severity**: Critical, High, Medium, Low
- **Affected Package**: Which dependency has the issue
- **Description**: What the vulnerability allows (e.g., RCE, XSS, data exposure)

#### 2. Check Impact

Determine if the vulnerability affects your codebase:
- Is the vulnerable function/feature used in your code?
- Is the vulnerable version actually installed?
- Are there workarounds or mitigations available?

#### 3. Prioritize Remediation

| Severity | Action | Timeline |
|----------|--------|---------|
| Critical | Immediate update or patch | Within 24 hours |
| High | Plan update in next sprint | Within 1 week |
| Medium | Update in next release cycle | Within 1 month |
| Low | Monitor, update when convenient | Next major update |

#### 4. Remediate

**Option A: Update Package**
```bash
pip install --upgrade <package-name>
pip freeze > requirements.txt
```

**Option B: Pin Specific Safe Version**
```bash
# Edit requirements.txt
package-name==2.3.4  # Safe version without vulnerability
```

**Option C: Use Alternative Package**
- If no fix is available, consider switching to an alternative library
- Update code to use the new package

#### 5. Verify Fix

After updating:
```bash
safety check --file requirements.txt
```

Re-run tests to ensure compatibility:
```bash
pytest
```

### Example Triage Workflow

1. **CI reports vulnerability**:
   ```
   safety check found 1 vulnerability
   django==5.2.10 has CVE-2024-XXXXX (High severity)
   ```

2. **Investigate**:
   - Check Django security releases: https://www.djangoproject.com/weblog/
   - Verify if CVE affects your Django usage
   - Check if patch version is available

3. **Remediate**:
   ```bash
   # Update to patched version
   pip install Django==5.2.11
   pip freeze > requirements.txt
   ```

4. **Verify**:
   - Re-run safety check
   - Run test suite
   - Create PR with updated requirements.txt

### Making Security Scan Blocking

To make security scan block the pipeline on critical vulnerabilities, modify `.github/workflows/ci.yml`:

```yaml
- name: Run safety check
  run: |
    safety check --file requirements.txt
  # Remove: continue-on-error: true
```

Or add severity threshold:

```yaml
- name: Run safety check
  run: |
    safety check --file requirements.txt --severity high
```

### Alternative: Dependabot

GitHub Dependabot can also be enabled for automated dependency updates:

1. Create `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

2. Dependabot will:
   - Automatically create PRs for security updates
   - Test updates in CI
   - Allow team to review and merge

### Best Practices

1. **Regular Updates**: Review and update dependencies monthly
2. **Pin Versions**: Use exact versions in `requirements.txt` for reproducibility
3. **Monitor**: Subscribe to security advisories for critical packages
4. **Document**: Record vulnerability fixes in commit messages and PR descriptions
5. **Automate**: Consider enabling Dependabot for low-effort security updates

## Secrets and extension points

The current workflow does not require any secrets.
When extending CI in the future, common additions include:

### 1) Pushing Docker images to a registry

Possible requirements:

- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`
- `REGISTRY_HOST`

Add secrets in:
Repository → Settings → Secrets and variables → Actions → New repository secret

### 2) Build and publish .deb packages

Possible requirements:

- Credentials / deploy keys for internal APT repository
- Repo host information
- GPG signing keys

### 3) Integration tests

Possible extension points:

- Creating additional service containers
- Adding `docker compose` based integration stage
- Adding test data seeding
