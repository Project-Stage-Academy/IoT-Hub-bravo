# Demo 1: Device Registration and Telemetry Ingestion

## Table of Contents

- [Goal](#goal)
- [Preconditions](#preconditions)
- [Step 1. Start from a clean environment](#step-1-start-from-a-clean-environment)
- [Step 2. Verify services are healthy](#step-2-verify-services-are-healthy)
- [Step 3. Load seed data](#step-3-load-seed-data)
- [Step 4. Run simulator](#step-4-run-simulator)
- [Step 5. Verify ingestion](#step-5-verify-ingestion)
- [Simulator Modes Explained](#simulator-modes-explained)
- [Troubleshooting](#troubleshooting)
- [Cleanup (optional)](#cleanup-optional)

## Goal
Demonstrate that a registered device can successfully send telemetry data into the system using the simulator in HTTP mode, and that the data is persisted and observable in the backend.

This demo proves the **baseline end-to-end flow**:
- device exists in the system
- simulator generates valid payloads
- ingestion endpoint accepts telemetry
- data is stored correctly

---

## Preconditions

- Docker and Docker Compose are installed
- No running containers from previous runs
- Ports `8000` (API), `1883` (MQTT), and `5432` (DB) are free

---

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

## Step 4. Run simulator 

### HTTP mode
Run the simulator for an existing device:

```bash
docker compose exec web python simulator/run.py \
  --mode http \
  --device SN-A1-TEMP-0001 \
  --count 3 \
  --rate 1 \
  --value-generation random
```

What happens:
- simulator resolves the device from DB
- associated metrics are discovered via `device_metrics`
- random values are generated per metric
- 3 telemetry payloads are sent via HTTP `POST /api/telemetry/`

---

### MQTT mode

Start MQTT forwarder (subscriber → HTTP bridge) in a separate terminal:

```bash
docker compose exec web python simulator/mqtt_forwarder.py
```

Then run the simulator in MQTT mode:

```bash
docker compose exec web python simulator/run.py \
  --mode mqtt \
  --device SN-A1-TEMP-0001 \
  --count 3 \
  --rate 1 \
  --value-generation random
```

What happens:
- simulator publishes telemetry to MQTT topic `telemetry`
- `mqtt_forwarder` subscribes to the topic
- received messages are forwarded to HTTP ingestion endpoint
- backend processes telemetry identically to HTTP mode

---

### HTTP mode
- Simulator prints successful HTTP responses (201 or 200)
- No validation or server errors

### MQTT mode
- Simulator successfully publishes messages
- Forwarder logs received MQTT messages
- HTTP ingestion succeeds for forwarded payloads

---

Simulator output:
- No errors
- Each iteration prints a successful send message

Backend behavior:
- Ingestion endpoint accepts all requests
- Telemetry records are persisted

---
### Manual value generation (`--value-generation manual`)

- For **each iteration** (`--count`), user is prompted to enter values
- Suitable for demos and debugging
- Ensures full control over payload values

Example flow:
- Prompt for temperature
- Prompt for humidity
- Payload sent immediately

---

### Random value generation (`--value-generation random`)

- Configuration happens **once per metric** at startup
- Numeric metrics: user defines min/max range
- Boolean metrics: random `true/false`
- String metrics: random choice from user-provided enum
---

### Non-interactive value generation (`--value-generation non-interactive`)

- No prompts; uses safe defaults for random values
- Numeric metrics: random float between 0 and 100
- Boolean metrics: random `true/false`
- String metrics: default string "ok"
- Ideal for automated tests and CI pipelines

## Step 5. Verify ingestion

### Verify via database

```bash
docker compose exec db psql -U iot_user_db -d iot_hub_db
```

```sql
SELECT 
    d.serial_id          AS device,
    m.metric_type        AS metric,
    t.ts,
    t.value_jsonb,
    t.value_numeric,
    t.value_bool,
    t.value_str
FROM 
    telemetries t
    JOIN device_metrics dm  ON t.device_metric_id = dm.id
    JOIN metrics        m   ON dm.metric_id       = m.id
    JOIN devices        d   ON dm.device_id       = d.id
ORDER BY 
    t.ts DESC
LIMIT 6;
```

Expected:
- `device_serial = 'SN-A1-TEMP-0001'`
- `metrics` contains numeric values (e.g. temperature, humidity)

---

## Simulator Modes Explained

Detailed simulator documentation is available in:


- [docs/simulator.md](../simulator.md)


---

## Troubleshooting

- **404 — Device not found**: ensure fixtures were loaded correctly
- **405 — Method Not Allowed**: only POST method is allowed
- **400 — Bad Request**: verify payload schema

---

## Cleanup (optional)

To reset the environment after the demo:

```bash
docker compose down -v
```

This prepares the stack for the next demo scenario.

