# WebSocket Telemetry via Kafka

This document describes how telemetry flows from ingestion (HTTP API) to real-time WebSocket clients. Data flows through the database, Kafka, and Django Channels (channel layer / Redis).

---

## Flow summary

* **HTTP ingest**: client POST → `/api/telemetry/` → saved to DB → produced to Kafka (topic `telemetry.clean`).
* **Kafka**: the `telemetry.clean` topic contains validated JSON messages.
* **Consumer**: a separate process reads from `telemetry.clean` and calls `publish_telemetry_event` for each message.
* **Channel layer (Redis)**: events are broadcast to channel groups (`telemetry.global`, `telemetry.device.<serial_id>`, `telemetry.metric.<name>`).
* **WebSocket**: clients connect to `ws/telemetry/stream/` and receive events in real time.

---

## Architecture (brief)

```
[Client] POST /api/telemetry/ → Django (telemetry_create)
│
├→ Save to DB (Telemetry)
│
└→ Produce to Kafka (topic: telemetry.clean)
│
▼
[Kafka] topic: telemetry.clean ← Messages (JSON)
│
▼
[Consumer] run_telemetry_clean_consumer → Reads messages
│
└→ publish_telemetry_event()
│
▼
[Redis] Channel layer → Broadcast to groups (telemetry.global, telemetry.device., telemetry.metric.)
│
▼
[WebSocket] ws/telemetry/stream/ ← Clients receive events in real time
```

In short: HTTP ingest saves telemetry to the DB and publishes to Kafka. A Kafka consumer reads `telemetry.clean` and, for each message, calls `publish_telemetry_event`, which uses the Django channel layer (Redis) to send events to subscribers. WebSocket clients receive those events.

---

# 1. Telemetry ingestion (HTTP)

**Endpoint:** `POST /api/telemetry/`

**Request body (JSON):**

```json
{
  "schema_version": 1,
  "device": "MY-DEVICE-001",
  "metrics": {
    "temperature": 23.5,
    "humidity": 60
  },
  "ts": "2026-02-25T14:00:00Z"
}
```

**What happens in `telemetry_create`:**

* Verify the device exists and is active.
* Validate metrics: each metric must be linked to the device via `DeviceMetric`.
* Ensure value types match the metric type (`numeric`, `bool`, `str`).
* For each valid metric–value pair, create a DB row (`Telemetry`).
* For each saved pair, build one Kafka message with fields: `device_serial_id`, `device_id`, `metric`, `metric_type`, `value`, `ts`.
* Produce messages to topic `telemetry.clean` **after** successful DB save.
* If the device or any metric is invalid, return an API error (for example, "Device not found.") and do not publish to Kafka.

---

# 2. Kafka (topic: `telemetry.clean`)

* Only validated, DB-persisted telemetry is written to `telemetry.clean`.
* **Example message value (JSON):**

```json
{
  "device_serial_id": "MY-DEVICE-001",
  "device_id": 1,
  "metric": "temperature",
  "metric_type": "numeric",
  "value": 23.5,
  "ts": "2026-02-25T14:00:00Z"
}
```

* `ts` in the message is always an ISO-formatted string.
* The topic must exist before the consumer runs (or be auto-created by the broker on first produce). If the topic is missing, the consumer will log errors such as "Unknown topic or partition".

---

# 3. Kafka consumer (`run_telemetry_clean_consumer`)

* The consumer is a separate process (Django management command) that continuously reads from `telemetry.clean`.

**Run (Docker):**

```bash
docker compose exec web python manage.py run_telemetry_clean_consumer
```

**Behavior:**

* Subscribe to `telemetry.clean`.
* Read messages (JSON payload).
* For each message, `TelemetryCleanHandler` does:

  * Validate payload and `ts`.
  * Parse `ts` from ISO string to `datetime`.
  * Call `publish_telemetry_event`.
* If the consumer is not running, messages remain in Kafka and WebSocket clients receive no events. After starting, the consumer processes messages according to consumer group and offset settings.

---

# 4. Publishing the event (`publish_telemetry_event`)

* This function accepts one telemetry record and sends it to the channel layer (Django Channels, typically Redis).
* **Event payload:**

```json
{
  "event_id": "<uuid>",
  "type": "telemetry.update",
  "schema_version": 1,
  "sent_at": "2026-02-25T14:00:01.123456+00:00",
  "data": {
    "device_serial_id": "MY-DEVICE-001",
    "device_id": 1,
    "metric": "temperature",
    "metric_type": "numeric",
    "value": 23.5,
    "ts": "2026-02-25T14:00:00Z"
  }
}
```

* Targets: three channel groups:

  * `telemetry.global` — all subscribers.
  * `telemetry.device.{device_serial_id}` — per-device subscribers.
  * `telemetry.metric.{metric}` — per-metric subscribers.

* If the channel layer is not configured or Redis is down, events are not sent and WebSocket clients receive nothing.

---

# 5. WebSocket (client)

* **URL:** `ws://<host>/ws/telemetry/stream/?token=<JWT_ACCESS_TOKEN>`
* **Authentication:** required. Obtain JWT via `POST /api/auth/login/`.

  * The token must include role `admin` or `client`; otherwise the connection is closed (e.g. code 4403).

**Optional query filters:**

* `device` — only events for this device `serial_id`.
* `metric` — only events for this metric name.

**Examples:**

* All events:

```
ws://localhost:8000/ws/telemetry/stream/?token=...
```

* Events for a single device:

```
ws://localhost:8000/ws/telemetry/stream/?token=...&device=MY-DEVICE-001
```

* Events for a single metric:

```
ws://localhost:8000/ws/telemetry/stream/?token=...&metric=temperature
```

**WebSocket message format:**

```json
{
  "event_id": "uuid-...",
  "type": "telemetry.update",
  "schema_version": 1,
  "sent_at": "2026-02-25T14:00:01.123456+00:00",
  "data": {
    "device_serial_id": "MY-DEVICE-001",
    "device_id": 1,
    "metric": "temperature",
    "metric_type": "numeric",
    "value": 23.5,
    "ts": "2026-02-25T14:00:00Z"
  }
}
```

One such object is sent per telemetry event that completed the full path: HTTP → DB → Kafka → consumer → `publish_telemetry_event` → channel layer → WebSocket.

---

# Components (code locations)

| Component             | Location                                                                    |
| --------------------- | --------------------------------------------------------------------------- |
| HTTP ingest           | `apps.devices.views.telemetry_views`                                        |
| DB + Kafka produce    | `apps.devices.services.telemetry_services.telemetry_create`                 |
| Kafka produce         | `apps.devices.services.telemetry_kafka_service.produce_telemetry_clean`     |
| Topic                 | `telemetry.clean`                                                           |
| Consumer command      | `apps.devices.management.commands.run_telemetry_clean_consumer`             |
| Kafka handler         | `apps.devices.kafka_handlers.telemetry_clean_handler.TelemetryCleanHandler` |
| Channel layer publish | `apps.devices.services.telemetry_stream_publisher.publish_telemetry_event`  |
| WebSocket route       | `ws/telemetry/stream/` in `apps.devices.routing`                            |
| WebSocket consumer    | `apps.devices.consumers.telemetry_consumer.TelemetryConsumer`               |

---

# Requirements for the flow to work

* DB: `Device` (active), `Metric`, and `DeviceMetric` linking devices to metrics must exist.
* Kafka: broker up; topic `telemetry.clean` present (or auto-create enabled).
* Redis: channel layer configured in Django Channels.
* Consumer: `run_telemetry_clean_consumer` process running.
* WebSocket: valid JWT in the query containing role `admin` or `client`.

If any component is missing, events may not reach WebSocket clients. See `kafka.md` for Kafka and topic details.

---

# Quick verification

1. Start the consumer:

```bash
docker compose exec web python manage.py run_telemetry_clean_consumer
```

2. Get JWT: `POST /api/auth/login/` with username and password.
3. Open WebSocket: `ws://localhost:8000/ws/telemetry/stream/?token=<access_token>`.
4. Send telemetry: `POST /api/telemetry/` with a valid `device` (serial_id), `metrics`, and `ts`.
5. A new message with `type: "telemetry.update"` should appear in the WebSocket.

If nothing arrives, check consumer logs, the `telemetry.clean` topic (Kafka UI/CLI), and Redis (channel layer).

---

# Notes

* Validation at ingest ensures only correct, DB-persisted records are published to Kafka.
* Consider adding monitoring/alerts for the consumer, health checks for Redis and Kafka, and consumption metrics for the topic.
