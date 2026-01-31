
# Database Schema

## Table of Contents
- [Entity Relationship Diagram](#entity-relationship-diagram)
- [Recommended Indexes](#recommended-indexes)
- [TimescaleDB Hypertable Setup](#timescaledb-hypertable-setup)
- [Query Optimization Examples](#query-optimization-examples)
- [Database Backup and Recovery](#database-backup-and-recovery)
- [Data Seeding](#data-seeding)

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ DEVICES          : "owns"
    DEVICES ||--o{ DEVICE_METRICS : "has"
    METRICS ||--o{ DEVICE_METRICS : "is measured on"
    DEVICE_METRICS ||--o{ TELEMETRIES     : "records"
    DEVICE_METRICS ||--o{ RULES           : "triggers"
    RULES          ||--o{ EVENTS          : "generates"

    USERS {
        int      id          PK "serial, auto-increment"
        varchar  username    UK "unique, not null, max 150"
        varchar  email       UK "unique, not null, max 255"
        varchar  password    "not null, max 255"
        enum     role        "admin / client, default: client"
        timestamp created_at "default: CURRENT_TIMESTAMP"
        timestamp updated_at "default: CURRENT_TIMESTAMP"
    }

    DEVICES {
        int      id          PK "serial, auto-increment"
        varchar  serial_id   UK "unique, not null, max 255"
        varchar  name        "not null, max 255"
        text     description
        int      user_id     FK "references users"
        boolean  is_active   "default: true"
        timestamp created_at "default: CURRENT_TIMESTAMP"
    }

    METRICS {
        int    id         PK "serial, auto-increment"
        citext metric_type UK "unique, not null"
        enum   data_type   "numeric / str / boolean, not null"
    }

    DEVICE_METRICS {
        int id          PK "serial, auto-increment"
        int device_id   FK "→ devices.id"
        int metric_id   FK "→ metrics.id"
    }

    TELEMETRIES {
        bigint      id               PK "bigserial, auto-increment"
        int         device_metric_id FK "→ device_metrics.id"
        jsonb       value_jsonb      "not null"
        numeric     value_numeric    "GENERATED ALWAYS AS ..."
        boolean     value_bool       "GENERATED ALWAYS AS ..."
        text        value_str        "GENERATED ALWAYS AS ..."
        timestamptz ts               "not null, default: now()"
        timestamptz created_at       "default: now()"
    }

    RULES {
        int     id                PK "serial, auto-increment"
        varchar name              "not null, max 255"
        text    description
        jsonb   condition         "not null"
        jsonb   action            "not null"
        boolean is_active         "default: true"
        int     device_metric_id  FK "→ device_metrics.id, not null"
    }

    EVENTS {
        bigint    id         PK "bigserial, auto-increment"
        timestamp timestamp
        int       rule_id    FK "→ rules.id, not null"
        timestamp created_at "default: CURRENT_TIMESTAMP, not null"
    }
```

## Recommended Indexes

| Table            | Index name                          | Columns                          | Type       | Purpose / Accelerated queries                                      |
|------------------|-------------------------------------|----------------------------------|------------|--------------------------------------------------------------------|
| users            | idx_users_role                      | role                             | normal     | Filtering by role (admin vs client)                                |
| devices          | idx_devices_user_id                 | user_id                          | normal     | Fast lookup of devices per user                                    |
| devices          | idx_devices_is_active               | is_active                        | normal     | Filtering active/inactive devices                                  |
| device_metrics   | uq_device_metric                    | device_id, metric_id             | **unique** | Prevent duplicate metric assignments per device                    |
| device_metrics   | idx_device_metrics_device           | device_id                        | normal     | Quick access to all metrics of a device                            |
| device_metrics   | idx_device_metrics_metric           | metric_id                        | normal     | Quick access to devices measuring a specific metric                |
| rules            | idx_rules_device_metric             | device_metric_id                 | normal     | Find rules for specific device+metric                              |
| rules            | idx_rules_is_active                 | is_active                        | normal     | Filter active rules quickly                                        |
| events           | idx_events_timestamp                | timestamp                        | normal     | Time-range queries, sorting events by time                         |
| events           | idx_events_rule                     | rule_id                          | normal     | Find all events triggered by a rule                                |
| telemetries      | unique_telemetry_per_metric_time    | device_metric_id, ts             | **unique** | Prevent duplicate measurements at same timestamp                   |
| telemetries      | idx_telemetries_metric_time         | device_metric_id, ts             | normal     | Fast time-series queries per metric (most frequent access pattern) |
| telemetries      | idx_telemetries_timestamp           | ts                               | normal     | Global time-range queries across all telemetry                     |


## DBML LINK
https://dbdiagram.io/d/IoT-db-696d114dd6e030a0245f8e22

---

## TimescaleDB Hypertable Setup
To optimize the storage of high-frequency telemetry data, we use **TimescaleDB Hypertables**. This partitions the telemetry data by time, ensuring fast queries even with millions of records.

### Automated Setup
By default, you do **not** need to run this command manually. The hypertable creation script is integrated into the `entrypoint.sh` and executes automatically every time the `web` container starts, immediately after migrations are applied.

### Manual Execution
If you need to manually trigger the hypertable creation (e.g., after database maintenance or if you've manually cleared the database schema), use the following management command:

```bash 
docker compose exec web python manage.py setup_timescaledb
```

> ⚠️ **PRODUCTION WARNING**: Hypertable creation is **irreversible without data loss**. Once created, converting back to a regular table requires either:
> - Exporting all data and reimporting
> - Deleting all data in the table
> 
> **Always test in a staging environment first and ensure you have a full backup before running this command in production.**

### Testing the Setup Command

Integration tests are available to verify the `setup_timescaledb` command works correctly:

**Run all tests:**
```bash
docker compose exec web pytest apps/devices/tests/test_setup_timescaledb_integration.py -v
```

**Run specific test:**
```bash
docker compose exec web pytest apps/devices/tests/test_setup_timescaledb_integration.py::TestSetupTimescaleDBIntegration::test_dry_run_flag_does_not_modify_database -v
```

**Available test cases (15 total):**

**Integration Tests (TestSetupTimescaleDBIntegration):**
- `test_setup_timescaledb_runs_without_error` - Basic command execution
- `test_dry_run_flag_does_not_modify_database` - Verifies `--dry-run` flag
- `test_force_flag_bypasses_hypertable_check` - Verifies `--force` flag
- `test_dry_run_and_force_together` - Tests combined flags
- `test_command_with_no_flags` - Default execution path

**Extension Checks (TestSetupTimescaleDBExtensionChecks):**
- `test_extension_not_available_exits_with_error` - Extension not found error handling
- `test_extension_available_but_not_installed_shows_notice` - Extension availability vs installation
- `test_extension_already_installed_skips_notice` - Skips notice when installed

**Hypertable Checks (TestSetupTimescaleDBHypertableChecks):**
- `test_table_already_hypertable_exits_without_force` - Early exit when already hypertable
- `test_table_not_yet_hypertable_proceeds_with_setup` - Proceeds when not yet hypertable

**Dry-Run Tests (TestSetupTimescaleDBDryRun):**
- `test_dry_run_shows_all_six_sql_steps_exactly` - Verifies all SQL steps displayed
- `test_dry_run_shows_cleaned_sql_without_extra_whitespace` - SQL formatting validation

**Error Handling (TestSetupTimescaleDBErrorHandling):**
- `test_sql_steps_executed_in_atomic_transaction` - Transaction atomicity verification
- `test_database_error_shows_full_traceback_in_debug_mode` - Debug mode tracebacks
- `test_operational_error_during_execution_caught_and_reported` - OperationalError handling

**Test flags:**
```bash
# Verbose output
docker compose exec web pytest apps/devices/tests/test_setup_timescaledb_integration.py -v

# Include print statements
docker compose exec web pytest apps/devices/tests/test_setup_timescaledb_integration.py -v -s

# Stop on first failure
docker compose exec web pytest apps/devices/tests/test_setup_timescaledb_integration.py -x
```
- [Testing Setup](PYTEST_SETUP.md) - Pytest configuration and testing guide


---

## Query Optimization Examples

### Query Optimization for Telemetry Data

This document demonstrates how the `telemetries` table is optimized for common IoT use cases using TimescaleDB hypertable partitioning, indexes, and compression.

### Table Optimization Summary

- **Hypertable partitioning**: by `ts` (7-day chunks)
- **Indexes**:
  - `idx_telemetries_metric_time` (device_metric_id, ts)
  - `idx_telemetries_timestamp` (ts)
- **Constraint**:
  - UNIQUE (device_metric_id, ts) — prevents duplicate measurements for the same metric at the same time
- **Compression**: enabled for chunks older than 30 days (segment by `device_metric_id`, order by `ts DESC`)
- **Retention**: data older than 1 year is automatically dropped

All examples below were executed on a database with seeded test data (January 23, 2026).

### 1. Last 100 measurements for a specific metric (by device_metric_id)

**Query**:

```sql
EXPLAIN ANALYZE
SELECT 
    ts,
    value_numeric,
    value_bool,
    value_str
FROM telemetries
WHERE device_metric_id = 123
ORDER BY ts DESC
LIMIT 100;
```

<details>
<summary><b>EXPLAIN ANALYZE Output</b> (click to expand)</summary>

```
Limit  (cost=4.47..4.48 rows=3 width=61) (actual time=0.812..0.823 rows=0 loops=1)
   ->  Sort  (cost=4.47..4.48 rows=3 width=61) (actual time=0.811..0.821 rows=0 loops=1)
         Sort Key: _hyper_1_1_chunk.ts DESC
         Sort Method: quicksort  Memory: 25kB
         ->  Bitmap Heap Scan on _hyper_1_1_chunk  (cost=1.27..4.45 rows=3 width=61) (actual time=0.098..0.108 rows=0 loops=1)
               Recheck Cond: (device_metric_id = 123)
               ->  Bitmap Index Scan on _hyper_1_1_chunk_telemetries_device_metric_id_dffeeb4b  (cost=0.00..1.27 rows=3 width=0) (actual time=0.095..0.105 rows=0 loops=1)
                     Index Cond: (device_metric_id = 123)
 Planning Time: 11.316 ms
 Execution Time: 1.170 ms
```

</details>
 **This query is optimized by:**

1. Using the composite index `idx_telemetries_metric_time` (device_metric_id, ts) to instantly filter by metric and enable backward scan for newest-first order  
2. Leveraging TimescaleDB chunk exclusion — only relevant time chunks are considered  
3. Early termination when no matching rows exist — no chunk scan or JSONB decompression needed

### 2. Recent measurements with device name, metric type, and values

```sql
EXPLAIN ANALYZE
SELECT 
    d.serial_id,
    d.name AS device_name,
    m.metric_type AS metric_type,
    t.ts,
    t.value_numeric,
    t.value_bool,
    t.value_str
FROM telemetries t
JOIN device_metrics dm ON t.device_metric_id = dm.id
JOIN devices d ON dm.device_id = d.id
JOIN metrics m ON dm.metric_id = m.id
WHERE d.id = 789                           
AND t.ts >= NOW() - INTERVAL '24 hours'
ORDER BY t.ts DESC;
```

<details>
<summary><b>EXPLAIN ANALYZE Output</b> (click to expand)</summary>

```
Sort  (cost=23.89..23.89 rows=1 width=1311) (actual time=0.456..0.472 rows=0 loops=1)
   Sort Key: t.ts DESC
   Sort Method: quicksort  Memory: 25kB
   ->  Nested Loop  (cost=1.78..23.88 rows=1 width=1311) (actual time=0.373..0.389 rows=0 loops=1)
         ->  Nested Loop  (cost=1.63..22.71 rows=1 width=1097) (actual time=0.372..0.388 rows=0 loops=1)
               ->  Nested Loop  (cost=1.49..20.34 rows=1 width=69) (actual time=0.372..0.387 rows=0 loops=1)
                     ->  Bitmap Heap Scan on device_metrics dm  (cost=1.33..8.57 rows=10 width=12) (actual time=0.371..0.385 rows=0 loops=1)
                           Recheck Cond: (device_id = 789)
                           ->  Bitmap Index Scan on device_metrics_device_id_aedc7780  (cost=0.00..1.33 rows=10 width=0) (actual time=0.368..0.381 rows=0 loops=1)
                                 Index Cond: (device_id = 789)
                     ->  Custom Scan (ChunkAppend) on telemetries t  (cost=0.15..1.17 rows=1 width=65) (never executed)
                           Order: t.device_metric_id
                           Chunks excluded during startup: 0
                           ->  Index Scan using _hyper_1_1_chunk_idx_telemetries_metric_time on _hyper_1_1_chunk t_1  (cost=0.15..1.17 rows=1 width=65) (never executed)
                                 Index Cond: ((device_metric_id = dm.id) AND (ts >= (now() - '24:00:00'::interval)))
               ->  Index Scan using devices_pkey on devices d  (cost=0.14..2.36 rows=1 width=1036) (never executed)
                     Index Cond: (id = 789)
         ->  Index Scan using metrics_pkey on metrics m  (cost=0.15..1.16 rows=1 width=222) (never executed)
               Index Cond: (id = dm.metric_id)
 Planning Time: 35.270 ms
 Execution Time: 1.308 ms
```

</details>


---

## Database Backup and Recovery

This guide provides instructions for creating database snapshots, automating the backup process, and verifying data integrity.

> ⚠️ **PRODUCTION WARNING**: Always test backup and restore procedures in a staging environment before relying on them in production. Ensure backups are stored securely and regularly tested for integrity.

### 1. Manual Backup (Custom Format)

**To create a manual backup:**

```bash
# 1. Ensure the backup directory exists on your host machine
mkdir -p backups

# 2. Run the dump command
# The output is redirected to a file on your host machine
docker compose exec -T db pg_dump \
  -U iot_user_db -d iot_hub_db \
  --format=custom \
  --no-owner --no-privileges \
  > backups/iot_hub_$(date +%Y%m%d_%H%M%S).dump
```

### 2. Restore Procedure
To restore data from a .dump file, we use pg_restore. 

**To restore into a test database:**

```bash
# 1. Create a clean database for verification
docker compose exec db psql -U iot_user_db -d postgres -c "DROP DATABASE IF EXISTS iot_db_test;"
docker compose exec db psql -U iot_user_db -d postgres -c "CREATE DATABASE iot_db_test;"

# 2. Enable TimescaleDB to restore
docker compose exec db psql -U iot_user_db -d iot_db_test \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"


# 3. Restore the data (using 4 parallel jobs for better performance)
docker compose exec -i -T db pg_restore \
  -U iot_user_db \
  -d iot_db_test \
  --no-owner \
  --no-privileges \
  < backups/snapshot_20260124_022006.dump #set your backup file name
```


[!IMPORTANT] Note the -i flag and the < operator. This pipes the file from your host machine into the Docker container.

### 3. Automated Daily Backup Script

The backup script is maintained in [scripts/backup_db.sh](../scripts/backup_db.sh) to avoid duplication with this documentation.

**Setup instructions:**
* Make it executable: `chmod +x scripts/backup_db.sh`
* Run manually: `./scripts/backup_db.sh`
* View the full script: See [scripts/backup_db.sh](../scripts/backup_db.sh)

The script includes:
- Automatic timestamped backup creation
- Custom PostgreSQL dump format for efficiency
- Automatic cleanup of backups older than 7 days
- Detailed logging of backup operations

### 4. Scheduling with Cron

To automate backups on a server, add the script to the system's `crontab`.
* Open crontab: `crontab -e`
* Add the following line (runs daily at 7:00 AM):
```bash
0 7 * * * cd /path/to/your/project && ./scripts/backup_db.sh >> backups/backup.log 2>&1
```
* `:wq` to save
---

## Data Seeding

### Overview

The `seed_dev_data` management command populates the database with fixture data for development and testing. It is **idempotent**, meaning it can be safely run multiple times without corrupting data.

Specifically, it does the following:

* **Default Users & Roles:**
Creates predefined users with assigned roles and passwords:

> dev_admin – Admin role (UserRole.ADMIN), password: DevSecurePass

> alex_client – Client role (UserRole.CLIENT), password: ClientAccess1

> jordan_client – Client role (UserRole.CLIENT), password: ClientAccess2

These users are created or updated depending on the current state of the database.

* **Sample Devices:**
Registers initial IoT devices for testing. Devices are dynamically assigned to client users (alex_client and jordan_client) to simulate realistic ownership.

* **Metrics & Bindings:**
Sets up device metrics (e.g., temperature, humidity, battery level) and binds them to devices. Metrics are loaded in the correct dependency order to ensure consistency.

* **Telemetry Data:**
Populates sample telemetry readings for devices, providing realistic time-series data that can be used for testing dashboards, rules, and aggregations.

* **Initial Rules & Events:**
Defines default business logic rules and populates sample events to simulate triggers and actions within the system.

* **Execution Options:**

```--force```: Clears existing seeded data and recreates it from fixtures. Ensures a clean state for development testing.

```--dry-run```: Simulates the seeding process without writing anything to the database. Useful for verifying fixture validity and sequence order.

**Notes:**

* The devices fixture is generated dynamically to assign users correctly; a temporary JSON file is created for this purpose and automatically cleaned up after loading.

* This command is safe to run multiple times; --force ensures a full refresh, while running without it will fail if seeded data already exists.

### Automatic Seeding

By default, seeding runs automatically when the container starts:

```bash
docker compose up
```

To disable automatic seeding, set in `.env`:
```env
ENABLE_SEED_DATA=false
```

### Manual Seeding

To manually trigger data seeding:

```bash
docker compose exec web python manage.py seed_dev_data
```

### Resetting Seeded Data

To clear all seeded data and start fresh:

```bash
# Delete all data (destructive)
docker compose exec web python manage.py flush

# Then re-seed
docker compose exec web python manage.py seed_dev_data
```

> ⚠️ **WARNING**: `flush` removes **all** database data, including any data you've manually created. Use only in development environments.


### Verification

To verify that seeding was successful, check the data:

```bash
# Count users
docker compose exec web python manage.py shell -c "from apps.users.models import User; print(f'Users: {User.objects.count()}')"

# Count devices
docker compose exec web python manage.py shell -c "from apps.devices.models import Device; print(f'Devices: {Device.objects.count()}')"

# Count telemetry records
docker compose exec web python manage.py shell -c "from apps.devices.models import Telemetry; print(f'Telemetry records: {Telemetry.objects.count()}')"
```