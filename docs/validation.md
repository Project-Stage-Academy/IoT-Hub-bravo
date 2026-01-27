# Validation log
This document records a cold-start validation run to confirm the local Docker development environment works from a fresh clone.

Notes:
- The convenience scripts (`./scripts/*.sh`) are intended for **macOS/Linux**.
- On Windows, use the **equivalent Docker Compose commands** (or run scripts via WSL/Git Bash).

## Cold start

### 1) Clone repository

```bash
git clone <repo-url>
cd iot-catalog-hub
```

### 2) Create environment file
```bash
cp .env.example .env
```

### 3) Make scripts executable (macOS/Linux)
```bash
chmod +x scripts/*.sh
```

### 4) Start development environment

Build images and start containers using Docker Compose

macOS/Linux:
```bash
./scripts/up.sh
```

Windows:
```bash
docker compose up -d --build
```

### 5) Confirm containers are running

Ensure Docker Compose created containers and they are not exiting/crashing

```bash
docker compose ps
```


### 6) Open the service in a browser

Confirm the app is reachable from host and routing works

- Web: http://localhost:8000
- Admin: http://localhost:8000/admin/
- Swagger: http://localhost:5433/
- Flower: http://localhost:5555/


## Expected results

- `./scripts/up.sh` or `docker compose up -d --build` succeeded
- Containers are built and healthy
- Migrations applied successfully
- Service available at http://localhost:8000
- Django admin available at http://localhost:8000/admin/
- Swagger UI available at http://localhost:5433/
- Flower available at http://localhost:5555/
