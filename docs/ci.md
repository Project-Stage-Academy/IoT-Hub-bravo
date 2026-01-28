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

The pipeline is split into three jobs with strict ordering:

1. `lint` → 2. `test` → 3. `build`

The dependency chain is enforced with `needs`:

- `test` runs only if `lint` succeeds
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

### 2) Test job

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

### 3) Build job

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

### 3) Build Docker image locally

```bash
docker build -f ./docker/django/Dockerfile -t iot-hub/django:local .
```

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
