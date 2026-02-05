
# Smoke Tests (IoT Hub)

This guide explains how to run the smoke tests and what each script validates.

---

## Prerequisites

- Docker Compose v2 available (`docker compose`).
- Services up: `web`, `db`, and for MQTT smoke test also `mosquitto`.
- Your current directory is the project root (where `docker-compose.yml` is located).
Start the stack:

```bash
docker compose down -v

docker compose up -d --build
```

---

## Smoke Scripts Overview

Scripts are located in [backend/scripts/smokes](backend/scripts/smokes).

### 1) Seed demo data

**Script:** [backend/scripts/smokes/smoke_seed_dev_data.sh](backend/scripts/smokes/smoke_seed_dev_data.sh)

**Purpose:**
- Seeds demo data using `seed_dev_data`.
- Verifies core objects exist (devices, rules).
- Ensures idempotency (counts don’t change on a second run).

**Make file executable (if needed):**

```bash
chmod +x ./backend/scripts/smokes/smoke_seed_dev_data.sh
```

**Run:**

```bash
./backend/scripts/smokes/smoke_seed_dev_data.sh
```

**Expected result:**
- “Core objects exist” printed.
- Idempotency check passes.

---

### 2) HTTP simulator

**Script:** [backend/scripts/smokes/smoke_http_simulator.sh](backend/scripts/smokes/smoke_http_simulator.sh)

**Purpose:**
- Runs the telemetry simulator in HTTP mode.
- Confirms telemetry count increases after sending.

**Make file executable (if needed):**

```bash
chmod +x ./backend/scripts/smokes/smoke_http_simulator.sh
```

**Run:**

```bash
./backend/scripts/smokes/smoke_http_simulator.sh
```

**Expected result:**
- Telemetry count after run is greater than before.

**Notes (from simulator docs):**
- Simulator uses `--mode http` with random values(`--non-interactive`). See [docs/simulator.md](docs/simulator.md) for CLI arguments.
- Requires a valid device serial (default: `SN-A1-TEMP-0001`).
- Override device: `DEVICE_SERIAL=SN-A1-HUM-0002 ./backend/scripts/smokes/smoke_http_simulator.sh`

---

### 3) MQTT simulator

**Script:** [backend/scripts/smokes/smoke_mqtt_simulator.sh](backend/scripts/smokes/smoke_mqtt_simulator.sh)

**Purpose:**
- Runs the telemetry simulator in MQTT mode.
- Verifies telemetry count increases.

**Important (from simulator docs):**
- MQTT mode requires the MQTT → HTTP forwarder to be running. See [docs/simulator.md](docs/simulator.md).
- Start forwarder in a separate terminal:

```bash
docker compose exec web python simulator/mqtt_forwarder.py
```

If the forwarder is not running, MQTT messages will be published but telemetry will not reach the backend and the smoke test will fail.

**Make file executable (if needed):**

```bash
chmod +x ./backend/scripts/smokes/smoke_mqtt_simulator.sh
```

**Run:**

```bash
./backend/scripts/smokes/smoke_mqtt_simulator.sh
```

**Expected result:**
- Telemetry count after run is greater than before.

---

## Common Configuration Overrides

All scripts support environment overrides:

```bash
SERVICE=web DEVICE_SERIAL=SN-A1-TEMP-0001 ./backend/scripts/smokes/smoke_http_simulator.sh
```

Useful variables:

- `SERVICE`: Docker Compose service running Django (default `web`).
- `DEVICE_SERIAL`: Device `serial_id` used by simulator scripts.
- `SIM_CMD`: Full simulator command if you need custom arguments.

---

## Troubleshooting

- **No devices/rules created:** run the seed script first or re-check DB connection.
- **Telemetry count not increasing (HTTP):** verify API is reachable and device exists.
- **Telemetry count not increasing (MQTT):** ensure `mosquitto` and the forwarder are running.
- **Device not found:** pick a valid serial from [docs/simulator.md](docs/simulator.md#valid-device-serial-ids).

---

## Quick Full Smoke Flow

```bash
docker compose up -d
./backend/scripts/smokes/smoke_seed_dev_data.sh
./backend/scripts/smokes/smoke_http_simulator.sh
docker compose exec web python simulator/mqtt_forwarder.py
./backend/scripts/smokes/smoke_mqtt_simulator.sh
```

