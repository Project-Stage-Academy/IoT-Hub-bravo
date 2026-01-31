# IoT Hub Demo Playbook

## Table of Contents

- [1. Pre-Demo Checks](#1-pre-demo-checks)

- [2. Resetting Seed Data Between Demos](#2-resetting-seed-data-between-demos)

- [3. Running the Simulator](#3-running-the-simulator)

- [4. Quick Troubleshooting](#4-quick-troubleshooting)

- [5. Pre-Demo Checklist](#5-pre-demo-checklist)

- [6. Post-Demo Cleanup](#6-post-demo-cleanup)

## Purpose
This playbook provides a step-by-step guide to prepare, run, and troubleshoot demo scenarios for IoT Hub. It includes pre-demo checks, seed data reset instructions, and common troubleshooting tips.

---

## 1. Pre-Demo Checks

Before running any demo, verify the following:

1. **Docker & Docker Compose**
   ```bash
   docker --version
   docker compose version
   ```

2. **Ports Availability**
   - `8000` — web/API
   - `5432` — PostgreSQL / TimescaleDB
   - `1883` — MQTT broker (mosquitto)

3. **No Running Containers**
   ```bash
   docker compose down -v
   ```

---

## 2. Resetting Seed Data Between Demos

1. Stop and remove containers/volumes:
   ```bash
   docker compose down -v
   ```

2. Start dev stack:
   ```bash
   docker compose up -d --build
   ```

3. Load fixtures:
   ```bash
   docker compose exec web python manage.py seed_dev_data
   ```

4. Verify devices:
   ```bash
   docker compose exec web python manage.py shell
   ```
   ```python
   from apps.devices.models import Device
   print(list(Device.objects.values_list("serial_id", flat=True)))
   ```

---

## 3. Running the Simulator

### Command
```bash
docker compose exec web python simulator/run.py \
  --mode <http|mqtt> \
  --device <serial_id> \
  --count <N> \
  --rate <messages_per_sec> \
  --value-generation <manual|random>
```

### Modes
- **HTTP**: sends telemetry to ingestion endpoint.
- **MQTT**: publishes to broker; can use MQTT forwarder to relay messages to HTTP endpoint.

### Value Generation
- **manual**: enter values for each metric per iteration.
- **random**: numeric metrics use min/max, string metrics use predefined set, boolean is random.
- **non-interactive**: uses safe defaults for random values without prompts (ideal for smoke tests/CI).

### Reference
See [`docs/simulator.md`](../simulator.md) for detailed instructions.

---

## 4. Quick Troubleshooting

| Issue | Symptoms | Solution |
|-------|---------|---------|
| 400 Bad Request | HTTP 400, payload rejected | Verify JSON schema, `schema_version`, metric names exist in DB |
| Device not found | HTTP 404 | Check fixtures loaded, serial_id exists |
| Connection refused (HTTP) | Port 8000 fails | Check `web` container running |
| Connection refused (MQTT) | Port 1883 fails | Ensure `mosquitto` container running |
| KeyboardInterrupt / crash | Simulator interrupted | Restart; MQTT forwarder: Ctrl+C once for graceful stop |
| Unhealthy container | `docker compose ps` shows `unhealthy` | Check logs: `docker compose logs <service>` |

---

## 5. Pre-Demo Checklist

1. All services running and healthy (`docker compose ps`).
2. Seed data loaded and verified.
3. Simulator dependencies installed.
4. Ports 8000, 5432, 1883 free.

---

## 6. Post-Demo Cleanup

```bash
docker compose down -v
```
Clears containers, networks, volumes for clean state.


