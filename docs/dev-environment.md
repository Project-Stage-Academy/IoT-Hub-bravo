# Developer environment

This repository provides a reproducible local developer environment for the monolithic MVP using Docker and Docker Compose.


## Requirements

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Docker Compose
- Git


## Compose files and intended usage

Two Compose files are used:

- `docker-compose.yml` — **base** configuration (Gunicorn, no live code mounts).
- `docker-compose.override.yml` — **development override** (bind-mount source code into the container and run Django `runserver`).

Docker Compose automatically loads `docker-compose.override.yml` when you run `docker compose ...` without `-f`.

**Security note**: `docker/django/Dockerfile` defines build-time `SECRET_KEY` environment variable,
which is an intentionally unsafe placeholder used only for `collectstatic` command. 
Runtime must supply a real secret key. Do not reuse the build placeholder in any environment.


### Base run
`docker compose -f docker-compose.yml up -d --build`


### Development run
Loads docker-compose.override.yml automatically and bind-mounts the source code

`docker compose up -d --build`


### What changes in dev mode
- `web` command is replaced with `start-web-dev.sh` script
- `worker` command is replaced with `celery -A conf.celery_app worker -l INFO` (no concurrency)
- `./backend` is mounted into `/app` inside `web` and `worker` containers for live code reload
- `static_data` named volume is mounted


## Convenience scripts

The repository provides simple shortcuts under `./scripts/`:

- `./scripts/up.sh`  
  Builds images (if needed) and starts the stack in the background (`docker compose up -d --build`).  
  Prints service URLs.

- `./scripts/down.sh`  
  Stops the stack (`docker compose down`). Does not remove volumes.

- `./scripts/logs.sh [container]`  
  Follows logs for all services or for a single service (example: `./scripts/logs.sh web`).

- `./scripts/reset-db.sh`  
  Resets only the database state by removing the Postgres volume and restarting the stack.
  Use this when you need a clean database.

Notes:
- Scripts are idempotent: running `up.sh` multiple times is safe.
- Dev mode is enabled automatically via `docker-compose.override.yml` when you run `docker compose ...` without `-f`.


### Make scripts executable (macOS/Linux)

From the repo root:

```bash
chmod +x scripts/*.sh
```


## DIND orchestration demo (lab/demo only)

This repository includes a Docker-in-Docker (DIND) demo runner that starts the Compose stack inside a privileged container.

### Security caveats
- **DIND requires `--privileged`**, which grants root-level capabilities inside the container.
- **Do not use DIND in production.** This is intended for local lab/demo usage only.
- Anything mounted into the DIND container (project source directory) can be accessed by processes inside it.
- Prefer running the stack directly via `docker compose` unless you specifically need the DIND demo.

### Run DIND demo
From the repository root:

```bash
./scripts/dind-up.sh
```

### Stop and remove the DIND container:

```bash
./scripts/dind-down.sh
```

If you change Compose files used by the demo, re-run ./scripts/dind-down.sh then ./scripts/dind-up.sh.


## Troubleshooting

### Rebuild images

If you suspect a stale Docker cache:

```bash
docker compose build --no-cache
docker compose up -d
```

### Reset database

If you need a clean Postgres volume:

```bash
./scripts/reset-db.sh
```

### Inspect health and container state
```bash
docker compose ps
```

Inspect a container state (replace <container>):
```bash
docker inspect --format '{{json .State}}' <container>
```

### View logs:

View all logs:
```bash
./scripts/logs.sh
```

View container logs (replace <container>):
```bash
./scripts/logs.sh <container>
```
