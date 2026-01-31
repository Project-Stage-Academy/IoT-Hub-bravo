# Demo 3: Streaming Aggregation Verification (Conceptual)

## Table of Contents

- [Goal](#goal)
- [Scope & Status](#scope--status)
- [Preconditions](#preconditions)
- [Step 1. Start from a clean environment](#step-1-start-from-a-clean-environment)
- [Step 2. Verify services are healthy](#step-2-verify-services-are-healthy)
- [Step 3. Load seed data](#step-3-load-seed-data)
- [Aggregation Model (Expected)](#aggregation-model-expected)
- [Step 1. Generate high-frequency telemetry](#step-1-generate-high-frequency-telemetry)
- [Step 2. Verify raw telemetry volume](#step-2-verify-raw-telemetry-volume)
- [Step 3. Conceptual aggregation checks](#step-3-conceptual-aggregation-checks)
- [Step 4. Cross-check simulator vs aggregation](#step-4-cross-check-simulator-vs-aggregation)
- [Expected Results (Conceptual)](#expected-results-conceptual)
- [Common Issues](#common-issues)
- [Why This Demo Exists](#why-this-demo-exists)
- [Cleanup](#cleanup)

---

## Goal
Demonstrate how telemetry data **can be aggregated over time windows** (e.g. average, min, max) once streaming/aggregation logic is enabled.

This demo is **conceptual by design**: it documents the expected behavior, data flow, and validation steps, even though the aggregation service or queries may not yet be fully implemented.

The purpose is to:
- define a clear contract for future streaming logic
- allow manual or partial verification today
- provide a ready-to-use demo once aggregation is enabled

---

## Scope & Status

**Current state**:
- Telemetry ingestion works (Demo 1)
- Rules are conceptual (Demo 2)
- Streaming aggregation is **not fully implemented yet**

**This demo verifies**:
- consistent telemetry flow
- sufficient data volume for aggregation
- expected aggregation semantics

---

## Preconditions

## Step 1. Start from a clean environment

Stop and remove all containers, volumes, and networks to ensure a clean state:

```bash
docker compose down -v
```

Then start the full dev stack:

```bash
docker compose up -d --build
```

---

## Step 2. Verify services are healthy

Check container status:

```bash
docker compose ps
```

Expected:
- `web` — running
- `db` — healthy
- `mosquitto` — healthy (for MQTT)

If any service is unhealthy, inspect logs before proceeding (e.g., docker compose logs mosquitto).

---

## Step 3. Load seed data

Use the idempotent management command to load fixtures:

```bash
docker compose exec web python manage.py seed_dev_data
```

Verify that devices exist:

```bash
docker compose exec web python manage.py shell
```

```python
from apps.devices.models import Device
Device.objects.values_list("serial_id", flat=True)
```

Expected output includes:
- `SN-A1-TEMP-0001`
- `SN-A1-HUM-0002`
- `SN-A1-PRES-0003`

---

```bash
docker compose up -d
```

Verify:
- `web` is running
- `db` is healthy

---

## Aggregation Model (Expected)

Target aggregation examples:

- **AVG temperature per device per 1 minute**
- **MIN / MAX humidity per device per 5 minutes**
- **COUNT telemetry points per metric**

These aggregations are expected to be computed by:
- streaming processor
- or TimescaleDB continuous aggregates

---

## Step 1. Generate high-frequency telemetry

Run simulator in random mode with higher rate:

```bash
docker compose exec web python simulator/run.py \
  --mode http \
  --device SN-A1-TEMP-0001 \
  --count 60 \
  --rate 2 \
  --value-generation random
```

This sends:
- ~120 telemetry points
- over ~30 seconds

---

## Step 2. Verify raw telemetry volume

Query telemetry table:

```sql
SELECT COUNT(*) AS telemetry_count
FROM telemetries t
JOIN device_metrics dm ON t.device_metric_id = dm.id
JOIN devices d ON dm.device_id = d.id
WHERE d.serial_id = 'SN-A1-TEMP-0001';
```

Expected:
- count increases according to simulator run

---

## Step 3. Conceptual aggregation checks

### Example: Average temperature

Expected logical query:

```sql
SELECT
    time_bucket('1 minute', t.ts)          AS bucket,
    AVG(t.value_numeric)                   AS avg_temp
FROM 
    telemetries t
    JOIN device_metrics dm ON t.device_metric_id = dm.id
    JOIN metrics        m  ON dm.metric_id       = m.id
    JOIN devices        d  ON dm.device_id       = d.id
WHERE 
    d.serial_id    = 'SN-A1-TEMP-0001'
    AND m.metric_type = 'temperature'
GROUP BY 
    bucket
ORDER BY 
    bucket DESC;
```

Expected behavior:
- values are averaged per minute
- no missing buckets for active periods

> Note: actual schema or query may differ depending on final implementation.

---

## Step 4. Cross-check simulator vs aggregation

Manually compare:
- simulator-generated ranges (e.g. 10–20°C)
- aggregated values fall within expected bounds

This validates:
- no data loss
- no type mismatch
- timestamps are parsed correctly

---

## Expected Results (Conceptual)

- Aggregations reflect incoming telemetry
- No duplicate or missing windows
- Aggregated values are stable and reproducible

---

## Common Issues

- **Empty aggregation** → streaming worker not running
- **Wrong averages** → timestamp parsing or bucketing issue
- **Gaps in time windows** → simulator rate too low

---

## Why This Demo Exists

Even without a finished aggregation engine, this demo:
- defines acceptance criteria
- documents intended queries
- prevents ambiguous behavior later

Once aggregation is implemented, this demo becomes **fully executable without changes**.

---

## Cleanup

```bash
docker compose down -v
```

Resets the environment for further demos.

