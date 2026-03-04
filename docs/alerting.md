# Ingestion Monitoring & Alerting
 
This document describes the real-time monitoring and alerting setup for the IoT Hub
ingestion pipeline. It covers custom Prometheus metrics, alert rules, the Grafana
dashboard, and operational notes for local development.
 
## 1. Overview
 
The monitoring system tracks the health of the telemetry ingestion pipeline end-to-end:
 
- **MQTT / Kafka → Celery worker → PostgreSQL** — message throughput, latency, errors
- **Rule engine** — how many rules are evaluated and triggered per message
- **Events** — how many events are created and how many remain unacknowledged
 
Metrics are exposed at `http://localhost:8000/prometheus/metrics` and scraped by
Prometheus every 15 seconds. Grafana visualises the data and Prometheus evaluates
alert rules continuously.
 
## 2. Custom Metrics
 
All metrics are defined in `backend/apps/common/metrics.py`.
 
### Ingestion metrics
 
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `iot_ingestion_messages_total` | Counter | `source`, `status` | Total messages received. `source`: `mqtt`/`kafka`. `status`: `success`/`error` |
| `iot_ingestion_latency_seconds` | Histogram | `source` | End-to-end processing time per message |
| `iot_ingestion_errors_total` | Counter | `source`, `error_type` | Errors by type: `parse_error`, `validation_error`, `db_error`, `handler_error` |
 
### Rule processing metrics
 
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `iot_rules_evaluated_total` | Counter | `rule_type` | Total rules evaluated per telemetry point |
| `iot_rules_triggered_total` | Counter | `rule_type` | Rules whose condition matched |
| `iot_rule_processing_seconds` | Histogram | — | Time to evaluate all rules for one telemetry point |
 
### Event metrics
 
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `iot_events_created_total` | Counter | `severity` | Events created: `info`, `warning`, `critical` |
| `iot_events_unacknowledged` | Gauge | — | Current count of unacknowledged events |
 
## 3. Alert Rules
 
Alert rules are defined in `devops/prometheus-alerts.yml` and loaded by Prometheus
automatically. You can view their current state at `http://localhost:9090/alerts`.
 
| Alert | Severity | Condition | Duration |
|-------|----------|-----------|----------|
| `HighIngestionErrorRate` | critical | Error rate > 5% | 2 min |
| `HighIngestionLatency` | warning | p95 latency > 2s | 5 min |
| `NoIngestionMessages` | warning | No messages received | 10 min |
| `HighRuleTriggerRate` | warning | Rule trigger rate > 80% | 5 min |
| `DjangoDown` | critical | Django unreachable | 1 min |
| `CeleryWorkerDown` | critical | Celery worker unreachable | 1 min |
 
Alert states:
- **inactive** — condition not met
- **pending** — condition met, waiting for duration threshold
- **firing** — alert is active
 
> **Note:** Alertmanager is not configured (out of scope for MVP). Alerts are
> visible in Prometheus UI and Grafana only. Manual intervention is required.
 
## 4. Grafana Dashboard
 
Dashboard name: **IoT Ingestion Monitoring**
URL: `http://localhost:3000`
 
| Panel | Type | Description |
|-------|------|-------------|
| Messages/sec | Stat | Current ingestion rate (last 5 min) |
| Error Rate | Stat | Percentage of failed messages |
| Latency p95 | Stat | 95th percentile processing time |
| Events Created | Stat | Total events created |
| Ingestion Throughput | Time series | Messages/sec over time by source |
| Ingestion Latency | Time series | p50 / p95 / p99 latency over time |
| Rules Processing | Time series | Rules evaluated and triggered per second |
| Events by Severity | Time series | Event creation rate by severity |
| Error Breakdown | Table | Error counts grouped by source and type |
 
## 5. Multiprocess Metrics Setup
 
Django web and Celery worker run as **separate processes**. Without special
configuration, metrics incremented in the worker would not be visible in the
Django `/prometheus/metrics` endpoint.
 
The solution is `prometheus_client` multiprocess mode: each process writes its
metrics to files in a shared directory, and the metrics endpoint aggregates them.
 
**Required environment variable:**
 
```
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
```
 
This is set in `.env` and shared between `web` and `worker` containers via a
named Docker volume `prometheus_multiproc` in `docker-compose.yml`.
 
The custom metrics endpoint is implemented in `backend/apps/common/views.py` and
registered at `prometheus/metrics` in `backend/conf/urls.py`.
 
## 6. Local Testing
 
**Send a test MQTT message:**
 
```bash
mosquitto_pub -h localhost -p 1883 -t "telemetry" -m \
  '{"schema_version": 1, "device": "SN-A1-TEMP-0001", "metrics": {"temperature": 25.5}, "ts": "2026-02-23T13:00:00Z"}'
```
 
**Verify the worker processed it:**
 
```bash
docker logs worker --tail 10
```
 
Expected output includes `created=1, item_errors=0`.
 
**Verify metrics are visible:**
 
```bash
curl -s http://localhost:8000/prometheus/metrics | grep iot_ingestion_messages_total
```
 
Expected output:
 
```
iot_ingestion_messages_total{source="mqtt",status="success"} 1.0
```
 
**Check Prometheus:** `http://localhost:9090` → query `iot_ingestion_messages_total`
 
**Check Grafana:** `http://localhost:3000` → IoT Ingestion Monitoring dashboard
 