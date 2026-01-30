# Demo 2: Rule Threshold Triggering (Conceptual / Stub)

## Table of Contents

- [Goal](#goal)
- [Scope of this demo](#scope-of-this-demo)
- [Preconditions](#preconditions)
- [Step 1. Start from a clean environment](#step-1-start-from-a-clean-environment)
- [Step 2. Verify services are healthy](#step-2-verify-services-are-healthy)
- [Step 3. Load seed data](#step-3-load-seed-data)
- [Assumed Rule Definition (Future State)](#assumed-rule-definition-future-state)
- [Step 1. Send telemetry BELOW threshold (manual mode)](#step-1-send-telemetry-below-threshold-manual-mode)
- [Step 2. Send telemetry ABOVE threshold (manual mode)](#step-2-send-telemetry-above-threshold-manual-mode)
- [Step 3. Repeat via MQTT transport](#step-3-repeat-via-mqtt-transport)
- [What this demo will validate in the future](#what-this-demo-will-validate-in-the-future)
- [Next steps](#next-steps)

---

## Goal
Demonstrate **how rule-based threshold triggering is expected to work** once rule evaluation and notification endpoints are fully implemented.

⚠️ **Important:** This demo is **conceptual**. At the moment:
- rule evaluation service is not wired end-to-end
- notification delivery is not implemented
- no public API exists to observe rule execution results

The purpose of this demo is to:
- document the intended behavior
- define reproducible simulator inputs
- serve as a reference for future implementation and validation

---

## Scope of this demo

This demo **does NOT** assert real notifications or rule execution.
Instead, it verifies:
- telemetry payloads that *should* trigger a rule
- telemetry payloads that *should not* trigger a rule
- correct simulator usage for deterministic threshold testing

Once rule evaluation is implemented, this demo can be converted into a fully automated verification.

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

## Assumed Rule Definition (Future State)

For demonstration purposes, assume the following rule exists:

```
Rule name: High temperature alert
Device: SN-A1-TEMP-0001
Metric: temperature
Condition: value > 30
Severity: warning
```

This rule is **not evaluated yet**, but defines the expected system behavior.

---

## Step 1. Send telemetry BELOW threshold (manual mode)

Use manual value generation to control metric values precisely.

```bash
docker compose exec web python simulator/run.py \
  --mode http \
  --device SN-A1-TEMP-0001 \
  --count 1 \
  --value-generation manual
```

When prompted:
- temperature → `22`
- humidity → `45`

### Expected behavior (current state)
- Telemetry is accepted and stored
- No errors returned

### Expected behavior (future state)
- Rule **does not trigger**
- No notification generated

---

## Step 2. Send telemetry ABOVE threshold (manual mode)

```bash
docker compose exec web python simulator/run.py \
  --mode http \
  --device SN-A1-TEMP-0001 \
  --count 1 \
  --value-generation manual
```

When prompted:
- temperature → `35`
- humidity → `50`

### Expected behavior (current state)
- Telemetry is accepted and stored

### Expected behavior (future state)
- Rule **triggers**
- Notification event is created
- Downstream consumers receive alert

---

## Step 3. Repeat via MQTT transport

Run the same test using MQTT to validate transport parity:

```bash
docker compose exec web python simulator/run.py \
  --mode mqtt \
  --device SN-A1-TEMP-0001 \
  --count 1 \
  --value-generation manual
```

### Expected behavior
- Payload format identical to HTTP
- Transport difference does not affect rule logic

---

## What this demo will validate in the future

Once rule evaluation is implemented, this demo will additionally verify:
- threshold evaluation correctness
- rule enable/disable behavior
- notification delivery
- event logging

---

## Next steps

- Implement rule evaluation service
- Expose rule execution results (API or logs)
- Convert this demo into an automated smoke test

