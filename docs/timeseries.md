# TimescaleDB Quick Guide

This guide covers basic scripts and queries for working with TimescaleDB.

If you are looking for instructions on how to set up TimescaleDB, you might be interested in reading [schema.md](https://github.com/Project-Stage-Academy/IoT-Hub-bravo/blob/15d31cacfa4326845f0e81c4ecaff02d31196ba1/docs/schema.md)

## Table of Contents
- Compression and Retention
- Developer instructions for table/partition monitoring and maintenance
- Telemetry data sampling 

---
## Compression and Retention (Manual)

TimescaleDB automatically supports compression and retention policies, meaning it can compress older chunks and remove outdated data without manual intervention. However, in IoT-Hub, we also provide manual Celery tasks to run compression and retention on-demand or on custom schedules.

---

### **Compression**
**Purpose:**
- Reduce storage usage by compressing older chunks of telemetry data.
- Improve query performance by reducing I/O for historical data.

**Key Task:** `scripts.DB.compress_chunks.compress_chunks`

**How it works:**

1. Connects to the TimescaleDB database.

2. Fetches a list of chunks from the telemetries hypertable.

3. Determines which chunks are eligible for compression (typically older than a configurable threshold).

4. Calls TimescaleDB's compress_chunk function for each eligible chunk.

5. Returns an updated list of chunks (compressed vs uncompressed) for verification.

**Commands:**
```bash
# Check that the worker container is running
docker ps --filter "name=worker"

# Start a Celery worker to enqueue tasks
docker-compose exec worker celery -A celery_app worker -l info

# Start Celery Beat to schedule tasks
docker-compose exec worker celery -A celery_app beat -l info
```

The results will be shown in the console. Alternatively, you can use the Flower UI to view task information. To access Flower, open `http://localhost:5555/`.

---

### **Retention/Deletion**

**Purpose:**

- Remove old telemetry data that is no longer needed for analysis.

- Keep the database size manageable.

**Key Task**: `scripts.DB.delete_chunks.delete_chunks`

**How it works**:

1. Connects to the TimescaleDB database.

2. Fetches a list of chunks before deletion.

3. Calls TimescaleDB's run_job function for the retention job configured on the hypertable.

4. Fetches a list of chunks after deletion.

5. Returns an updated list of chunks for verification.


> ⚠️ **WARNING**: Note: This action may cause data loss, so proceed with caution and make sure to create a backup before executing it.

**Commands:**
```bash
# Check that the worker container is running
docker ps --filter "name=worker"

# Start a Celery worker to enqueue tasks
docker-compose exec worker celery -A celery_app worker -l info

# Start Celery Beat to schedule tasks
docker-compose exec worker celery -A celery_app beat -l info
```

The results will be shown in the console. Alternatively, you can use the Flower UI to view task information. To access Flower, open `http://localhost:5555/`.

### Note:

Compression and retention policies are applied automatically after 30 days and 1 year, respectively. However, they can be executed manually at any time using the following commands:

```bash
# Run compression
docker compose exec web python scripts/DB/compress_chunks.py

# Run retention (delete old chunks)
docker compose exec web python scripts/DB/delete_chunks.py
```
---

## Monitoring and Maintenance

In addition to compression and retention, developers need to monitor table growth, chunk counts, and database health, and perform maintenance tasks like reindexing or vacuuming when necessary.

Docker allows you to run SQL queries inside the db container using the following command:
```bash
docker compose exec db psql -U <db-user> -d <db-name> -c <sql-query>
```
---

### Monitoring Table Size
Use PostgreSQL's built-in functions to track storage usage:

```sql
-- Total size of the table including indexes
SELECT pg_size_pretty(pg_total_relation_size('telemetries')) AS total_size;

-- Size of just the table data (excluding indexes)
SELECT pg_size_pretty(pg_relation_size('telemetries')) AS table_size;

-- Size of each index on the table
SELECT 
    i.indexname,
    pg_size_pretty(pg_relation_size(c.oid)) AS index_size
FROM pg_indexes i
JOIN pg_class c 
    ON c.relname = i.indexname
WHERE i.tablename = 'telemetries';
```

`pg_total_relation_size` includes all indexes and toast tables.
Use this to track growth over time and detect unexpected spikes in storage.

### Monitoring Chunk Counts

TimescaleDB splits hypertables into chunks. To see how many chunks exist:

```sql
-- List of chunks in hypertable
SELECT chunk_name
FROM timescaledb_information.chunks
WHERE hypertable_name = 'telemetries'
ORDER BY chunk_name;

-- Number of chunks for the hypertable
SELECT count(*) AS chunk_count
FROM timescaledb_information.chunks
WHERE hypertable_name = 'telemetries';
```
This helps track chunk growth and detect old chunks that might need compression or deletion.


### Reindexing

Indexes can become bloated over time. Reindex periodically if you notice query slowdowns:

```sql
-- Reindex a specific index
REINDEX INDEX idx_telemetries_metric_time;

-- Reindex the entire table
REINDEX TABLE telemetries;
```

Recommended after bulk insertions, deletions, or compression operations.
Can also be scheduled during low-traffic periods to reduce impact.

---

### Vacuuming

PostgreSQL requires VACUUM to reclaim space from deleted or updated rows:

```sql
-- Analyze table statistics and reclaim space
VACUUM ANALYZE telemetries;

-- For aggressive space reclamation (may lock table)
VACUUM FULL telemetries;
```
`VACUUM ANALYZE` updates planner statistics and is safe for regular use.

`VACUUM FULL` is more aggressive but can lock the table use carefully on production hypertables.

---

## Telemetry Sampling

In IoT-Hub, telemetry sampling is used to generate test or synthetic telemetry data for devices. This is useful for testing, performance benchmarking, or monitoring when real device data is not yet available.

**Purpose:**
- Populate the telemetries hypertable with synthetic records.

- Support load testing, query performance validation, and timeseries feature testing (compression, retention, indexing).

- Provide a repeatable and configurable way to generate large datasets.

**Commands:**
> ⚠️ **WARNING**: Sampling requires the database to be seeded before use. Make sure to run `seed_dev_data` or enable it in your `.env` file.

```bash
# Run sampling
docker compose exec web python manage.py load_telemetry <number-of-rows>
```