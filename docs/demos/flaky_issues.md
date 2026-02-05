# Demo Scenarios: Flaky Steps & Stabilization Checklist

This document records end-to-end validation results for all demo scenarios and identifies steps that need stabilization.

**Last Updated:** 2026-01-30  
**Testing Environment:** Fresh dev stack (`docker compose down -v && docker compose up -d --build`)

---

## Table of Contents

- [Validation Approach](#validation-approach)
- [Demo 1: Device Registration & Telemetry Ingestion](#demo-1-device-registration--telemetry-ingestion)
- [Demo 2: Rule Threshold Triggering](#demo-2-rule-threshold-triggering)
- [Demo 3: Streaming Aggregation](#demo-3-streaming-aggregation)
- [Cross-Demo Issues](#cross-demo-issues)
- [Stabilization Recommendations](#stabilization-recommendations)

---

## Validation Approach

Each demo is run on a **fresh environment** following these steps:

1. **Fresh stack**: `docker compose down -v && docker compose up -d --build`
2. **Service health check**: `docker compose ps` (all services healthy)
3. **Seed data**: `docker compose exec web python manage.py seed_dev_data`
4. **Execute demo steps** in sequence
5. **Record flaky steps** with errors, timing issues, or non-deterministic behavior

**Criteria for "Flaky":**
- Intermittent failures across runs
- Timing-dependent (race conditions)
- Missing dependencies (e.g., forwarder not running)
- Unclear or missing prerequisites
- Non-deterministic output

---

## Demo 1: Device Registration & Telemetry Ingestion

**File**: [docs/demos/demo_1_device_registration_and_telemetry_ingestion.md](demo_1_device_registration_and_telemetry_ingestion.md)

### Checklist

| Step | Description | Status | Issues |
|------|-------------|--------|--------|
| 1.1 | Fresh environment: `docker compose down -v` | ✅ Pass | None |
| 1.2 | Start stack: `docker compose up -d --build` | ✅ Pass | None |
| 1.3 | Verify services: `docker compose ps` | ✅ Pass | Timing: ~15-30s for all healthy |
| 1.4 | Seed data: `seed_dev_data` | ✅ Pass | Idempotent, reliable |
| 1.5 | Verify devices exist (shell query) | ✅ Pass | Returns expected serial IDs |
| 1.6 | HTTP simulator (random, count=3, rate=1) | ✅ Pass | Completes ~3 seconds |
| 1.7 | Verify DB records (SQL query) | ✅ Pass | Records visible immediately |
| 1.8 | MQTT simulator (requires forwarder) | ⚠️ **Flaky** | See [Issue 1.1](#issue-11-mqtt-forwarder-dependency) |

### Issue 1.1: MQTT Forwarder Dependency

**Description:**  
Demo 1 MQTT mode requires external forwarder, but this is not enforced or validated.

**Symptom:**  
- MQTT messages published but no telemetry appears in DB
- User assumes simulator failed, but forwarder was never started
- No clear error message

**Current Workaround:**  
Manual reminder to start forwarder in separate terminal.

**Fix Needed:**  
- Add validation step: check if forwarder is running before MQTT test
- Or embed forwarder check in simulator
- Document prominently in demo instructions

**Reproduction:**
```bash
# Start simulator WITHOUT forwarder
docker compose exec web python simulator/run.py \
  --mode mqtt --device SN-A1-TEMP-0001 --count 3 --value-generation non-interactive
# Check DB: no new telemetry appears
```

---

## Demo 2: Rule Threshold Triggering

**File**: [docs/demos/demo_2_rule_threshold_triggering_and_notification.md](demo_2_rule_threshold_triggering_and_notification.md)

### Checklist

| Step | Description | Status | Issues |
|------|-------------|--------|--------|
| 2.1 | Fresh environment setup | ✅ Pass | Same as Demo 1 |
| 2.2 | Seed data | ✅ Pass | Idempotent |
| 2.3 | Send telemetry BELOW threshold (manual) | ✅ Pass | Prompts work correctly |
| 2.4 | Send telemetry ABOVE threshold (manual) | ✅ Pass | Prompts work correctly |
| 2.5 | Verify no rule events (future state) | ❌ **Not Impl** | Rule evaluation not wired [Issue 2.1](#issue-21-rule-evaluation-not-implemented) |
| 2.6 | Repeat via MQTT transport | ⚠️ **Flaky** | Same forwarder dependency as Demo 1 |

### Issue 2.1: Rule Evaluation Not Implemented

**Description:**  
Rule evaluation service is not end-to-end wired; demo is conceptual only.

**Symptom:**  
- Telemetry is ingested
- No rule events or notifications appear
- No API to query rule execution results

**Current State:**  
This is expected and documented in demo. **Not a flaky issue**, just incomplete feature.

**Fix Timeline:**  
Requires implementation of:
1. Rule evaluation service
2. Event creation on threshold trigger
3. Notification delivery system

---

## Demo 3: Streaming Aggregation

**File**: [docs/demos/demo_3_streaming_aggregation_conceptual.md](demo_3_streaming_aggregation_conceptual.md)

### Checklist

| Step | Description | Status | Issues |
|------|-------------|--------|--------|
| 3.1 | Fresh environment setup | ✅ Pass | Same as Demo 1 |
| 3.2 | Seed data | ✅ Pass | Idempotent |
| 3.3 | Generate high-frequency telemetry (60 count, rate=2) | ✅ Pass | Completes ~30 seconds |
| 3.4 | Verify raw telemetry volume (SQL) | ✅ Pass | Counts correct |
| 3.5 | Cross-check simulator vs aggregation | ⚠️ **Flaky** | See [Issue 3.1](#issue-31-aggregation-not-enabled) |

### Issue 3.1: Aggregation Not Enabled

**Description:**  
Streaming aggregation logic is not implemented; demo is conceptual.

**Symptom:**  
- Raw telemetry exists
- Aggregation queries return data (if TimescaleDB works)
- But no continuous aggregates or streaming logic runs

**Current State:**  
Expected. Demo documents the expected behavior.

**Fix Timeline:**  
Requires implementation of aggregation service or TimescaleDB continuous aggregates.

---
