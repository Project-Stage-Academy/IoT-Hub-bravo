# Developer Onboarding Runbook

This runbook provides step-by-step instructions for a **fresh developer** to boot the IoT-Catalog-Hub MVP in a local environment.

---

## 1. Prerequisites

Before starting, ensure the following are installed:

* Docker Desktop (macOS/Windows) or Docker Engine (Linux)
* Docker Compose
* Git
* Python 3.10, Django

---

## 2. Clone the Repository

```bash
git clone <repository-url>
cd IoT-Hub-bravo
```

---

## 3. Environment Setup

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Configure key environment variables in `.env`:

* `SECRET_KEY` – generate a secure key for local development:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

* `DB_HOST` – use `db` for Docker Compose
* `DEBUG=True`
* `CORS_ALLOWED_ORIGINS` – set to your local frontend URLs (e.g., `http://localhost:3000`)

> **Note:** Do not commit `.env` with secrets.

---

## 4. Start Development Environment

Build Docker images and start all services:

```bash
docker compose up -d --build
```

This will:

* Build Docker images
* Start PostgreSQL / TimescaleDB
* Run Django migrations
* Seed initial development data (users, devices, metrics, rules)
* Start Django API Gateway & Admin UI
* Run in detached mode (`-d`)

---

## 5. Verify Containers

Check that all containers are running and healthy:

```bash
docker compose ps
```

All containers should show `Up` status and not crash.

---

## 6. Database Management (Manual)

If you make model changes or need to re-run seed data:

```bash
# Create new migrations after changing models
docker compose exec web python manage.py makemigrations

# Apply migrations
docker compose exec web python manage.py migrate

# Seed database manually
docker compose exec web python manage.py seed_dev_data
```

---

## 7. Create Superuser (Optional)

To access Django Admin:

```bash
docker compose exec web python manage.py createsuperuser
```

---

## 8. Run Tests

Ensure code is working correctly:

```bash
docker compose exec web pytest
```

All tests should pass.

---

## 9. Access the Application

* API and Admin UI: [http://localhost:8000](http://localhost:8000)
* Django Admin: [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 10. Notes / Tips

* Execute all commands from the project root.
* `.env` must not contain secrets in commits.
* Initial seed data includes test users, sample devices, and default rules.
* Use Admin UI or API to register additional test devices.
