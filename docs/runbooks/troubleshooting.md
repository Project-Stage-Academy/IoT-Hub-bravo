# Troubleshooting Guide

This guide helps developers and operators quickly diagnose and resolve **common issues** in the IoT-Catalog-Hub MVP.

---

## 1. Database Connection Failure

**Symptoms:** Django API or agents fail to connect to PostgreSQL / TimescaleDB.
**Diagnostics:**

```bash
docker compose logs web | grep -i "could not connect"
docker compose exec db pg_isready -U iot_user_db
```

**Fix:**

* Check `.env` variables: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`
* Ensure database container is running:

```bash
docker compose ps
```

* Apply migrations if DB is empty:

```bash
docker compose exec web python manage.py migrate
```

---

## 2. Docker Container Crashes

**Symptoms:** Any service container exits immediately.
**Diagnostics:**

```bash
docker compose logs <service_name>
docker compose ps
```

**Fix:**

* Check `.env` and required environment variables
* Rebuild container:

```bash
docker compose up -d --build
```

* Check for port conflicts or missing dependencies

---

## 3. MQTT Telemetry Not Received

**Symptoms:** Telemetry agents do not forward device messages.
**Diagnostics:**

```bash
docker compose logs mqtt
```

**Fix:**

* Ensure devices point to the correct host and port
* Verify message broker is running:

```bash
docker compose exec broker kafka-topics.sh --list --bootstrap-server broker:9092
```

* Restart ingestion agents if needed

---

## 4. Rule Engine Fails to Trigger

**Symptoms:** Rules are not evaluated, or events not sent downstream.
**Diagnostics:**

```bash
docker compose logs rules
docker compose exec broker kafka-console-consumer.sh --topic telemetry-events --from-beginning --bootstrap-server broker:9092
```

**Fix:**

* Ensure Rule Engine container is running
* Check connectivity to broker
* Verify rules exist in database:

```bash
docker compose exec web python manage.py shell
>>> from rules.models import Rule
>>> Rule.objects.all()
```

---

## 5. API / Admin UI Not Reachable

**Symptoms:** `http://localhost:8000` or `/admin` not accessible.
**Diagnostics:**

```bash
docker compose logs web
docker compose ps
curl http://localhost:8000/api/health/
```

**Fix:**

* Ensure `DEBUG=True` for local dev
* Check `ALLOWED_HOSTS` in `.env`
* Restart Django container:

```bash
docker compose restart web
```

---

## 6. Tests Failing After Changes

**Symptoms:** Automated tests fail after model or logic changes.
**Diagnostics:**

```bash
docker compose exec web python manage.py test
```

**Fix:**

* Apply new migrations:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

* Ensure seed data is applied for tests:

```bash
docker compose exec web python manage.py seed_db
```

---

## 7. Collecting Metrics and Logs

* Logs:

```bash
docker logs <service_name> -n <Number of last entries>
```

* Prometheus metrics:

```text
http://localhost:9090/prometheus/metrics
```

* Grafana dashboards:

```text
http://localhost:3000
```

> Always check logs and metrics together to pinpoint the source of failure.