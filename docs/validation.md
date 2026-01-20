# Validation log
This document records a cold-start validation run to confirm the local Docker development environment works from a fresh clone.


## Cold start steps

### 1) Clone repository

```bash
git clone <repo-url>
cd iot-catalog-hub
```


### 2) Create environment file

`cp .env.example .env`


### 3) Start development environment

Build images and start containers using Docker Compose

`docker compose up -d --build`


### 4) Confirm containers are running

Ensure Docker Compose created containers and they are not exiting/crashing

`docker compose ps`


### 5) Open the service in a browser

Confirm the app is reachable from host and routing works

- http://localhost:8000
- http://localhost:8000/admin/


## Expected results

- `docker compose up -d --build` succeeded
- Containers are built and healthy
- Migrations applied successfully
- Service available at http://localhost:8000
- Django admin available at http://localhost:8000/admin/
