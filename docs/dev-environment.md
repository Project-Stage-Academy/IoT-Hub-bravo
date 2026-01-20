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


### Base run
`docker compose -f docker-compose.yml up -d --build`


### Development run
Loads docker-compose.override.yml automatically and bind-mounts the source code

`docker compose up -d --build`


### What changes in dev mode
- command is replaced with `python manage.py runserver 0.0.0.0:8000`
- `./backend` is mounted into `/app` inside the container for live code reload
- `static_data` named volume is mounted
