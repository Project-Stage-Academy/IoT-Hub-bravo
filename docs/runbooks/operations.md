# Operations Runbook

This runbook documents **tested commands and procedures** for maintaining the IoT-Catalog-Hub MVP in development and staging environments.

---

## 1. Backup Database

### PostgreSQL / TimescaleDB Backup

```bash
# Backup database inside Docker Compose
docker compose exec db pg_dump -U iot_user_db -F c iot_hub_db > backup_iot_hub_$(date +%F).dump
```

* `-F c` — custom format, supports `pg_restore`
* The file `backup_iot_hub_YYYY-MM-DD.dump` will be created on the host machine inside the current directory.

> **Tip:** Keep backups versioned and avoid committing them to Git.

### Automating Backups

To avoid data loss, schedule regular backups using a cronjob (for on-premise servers) or CI workflows (for cloud environments).

#### Using cron (Linux)
```bash
# Edit cron jobs
crontab -e

# Example: daily backup at 2:00 AM
0 2 * * * docker compose exec db pg_dump -U iot_user_db -F c iot_hub_db > /path/to/backups/backup_iot_hub_$(date +\%F).dump
```
#### Using GitHub Actions (Cloud)

```yaml
name: Scheduled DB Backup

on:
  schedule:
    - cron: '0 2 * * *'  # daily at 2:00 AM UTC

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Run database backup
        run: |
          # Use temporary/test credentials in CI for security
          docker compose exec -T db pg_dump -U iot_user_db -F c iot_hub_db > backup_iot_hub_$(date +%F).dump

      - name: Upload backup artifact
        uses: actions/upload-artifact@v3
        with:
          name: db-backup
          path: backup_iot_hub_*.dump
```

> **Warning:** Never use production secrets in CI workflows without proper security measures. Prefer temporary/test credentials or dedicated backup accounts.

---

## 2. Restore Database

### Restore from a Backup File

> **Warning:** Never run `DROP DATABASE` on production data without verified backups. Always confirm you are operating in the intended environment before executing destructive commands.

```bash
# Drop existing database (optional, if resetting)
docker compose exec db psql -U iot_user_db -c "DROP DATABASE iot_hub_db;"
docker compose exec db psql -U iot_user_db -c "CREATE DATABASE iot_hub_db;"

# Restore
docker compose exec -T db pg_restore -U iot_user_db -d iot_hub_db < backup_iot_hub_YYYY-MM-DD.dump

```

* This restores **both schema and data**.
* Verify by connecting to DB:

```bash
docker compose exec db psql -U iot_user_db -d iot_hub_db -c "\dt"
```

---

## 3. Migrations

If you update models in Django:

```bash
# Generate migrations
docker compose exec web python manage.py makemigrations

# Apply migrations
docker compose exec web python manage.py migrate
```

* Always backup the database before applying migrations in staging/production.

---

## 4. Log Management

All services log to stdout/stderr inside Docker Compose.

### View Logs

```bash
docker compose logs -f
```

* `-f` — follow logs live
* Filter by service:

```bash
docker compose logs -f web        # Django
docker compose logs -f mqtt       # Telemetry agent
docker compose logs -f rules      # Rule Engine
docker compose logs -f stream     # Stream Processor
docker compose logs -f db         # PostgreSQL
```

### Rotate Logs

* In dev: usually handled automatically by Docker
* In production/staging: configure logrotate or Docker logging driver as needed

---

## 5. Health Checks

* Verify that all containers are running:

```bash
docker compose ps
```

* Check Prometheus metrics for system health:

```text
# e.g. http://localhost:9090/targets
```

* Check API endpoints:

```bash
curl http://localhost:8000/api/health/
```

---

## 6. Notes / Tips

* Always backup DB before destructive operations
* Apply migrations **only after backup**
* Use seed_db to repopulate development data if needed
* Logs and Prometheus dashboards are the primary tools for troubleshooting service failures
