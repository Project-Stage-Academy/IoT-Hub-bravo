# External Events Integration Guide
## Overview

**The External Events API** allows external systems (IoT platforms, monitoring systems, webhooks, etc.) to send events to the platform.

These events are:

1. Validated via serializer

2. Mapped to internal event structure

3. Published to Kafka

4. Processed asynchronously by internal consumers

5. Stored in the Events database

6. Trigger notifications or webhook deliveries

The endpoint is designed for **high-throughput asynchronous event ingestion**.

## Endpoint
`POST /api/events/external/`
### Authentication

The endpoint requires:

- JWT authentication

- User role: client or admin

Headers example:

```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

## Request Payload

External systems must send events in the following JSON format:
```json
{
  "source": "softserve-office",
  "external_event_id": "evt-123",
  "device_external_id": "SERIAL-123",
  "timestamp": "2026-03-16T15:06:59Z",
  "payload": {
    "rule_id": 12,
    "metric": "humidity",
    "value": 150,
    "threshold": 50,
    "telemetry_ts": "2026-03-16T20:55:00Z",
    "notification": {
      "channel": "telegram",
      "message": "Critical temperature alert!",
      "webhook": "https://webhook.site/XXXX"
    }
  }
}
```
## Field Description
| Field              | Type              | Description                                    |
| ------------------ | ----------------- | ---------------------------------------------- |
| source             | string            | Name of the external system sending the event  |
| external_event_id  | string            | Unique event identifier in the external system |
| device_external_id | string            | External device identifier                     |
| timestamp          | ISO 8601 datetime | Time when the event occurred                   |
| payload            | object            | Event-specific data                            |

### Payload fields

| Field        | Description                               |
| ------------ | ----------------------------------------- |
| rule_id      | ID of the rule triggered                  |
| metric       | Metric name (temperature, humidity, etc.) |
| value        | Measured metric value                     |
| threshold    | Threshold value (optional)                |
| telemetry_ts | Timestamp of the telemetry measurement    |
| notification | Optional notification configuration       |


## Notification Payload

Notifications may contain:
```json
{
  "channel": "telegram",
  "message": "Critical temperature alert!",
  "webhook": "https://webhook.site/XXXX"
}
```
Supported integrations typically use **webhooks**.

## Example Integration (IoT System)

Example using `curl`:

```
curl -X POST http://localhost:8000/api/events/external/ \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "factory-iot",
    "external_event_id": "sensor-evt-1001",
    "device_external_id": "SENSOR-77",
    "timestamp": "2026-03-16T15:06:59Z",
    "payload": {
      "rule_id": 12,
      "metric": "temperature",
      "value": 85,
      "telemetry_ts": "2026-03-16T15:05:10Z",
      "notification": {
        "channel": "telegram",
        "message": "Temperature exceeded threshold!",
        "webhook": "https://webhook.site/XXXX"
      }
    }
  }'
  ```
## API Response

If the event is accepted:
```json
{
  "status": "accepted",
  "accepted": 1,
  "skipped": 0,
  "errors": {}
}
```
HTTP Status:

```http
202 Accepted
```
## Duplicate Event Protection

Events are deduplicated using:

`event_uuid + rule_triggered_at`

Duplicates are skipped.

Example response:
```json
{
  "status": "rejected",
  "accepted": 0,
  "skipped": 1,
  "errors": {
    "0": "Duplicate event skipped"
  }
}
```

## Event Idempotency

Each external event is transformed into a deterministic UUID:

`event_uuid = md5(source + external_event_id + device_external_id)`

This ensures:

- consistent event identity

- deduplication protection

- safe retry handling

## Error Responses
Invalid JSON
`400 Bad Request`
```json
{
  "code": 400,
  "message": "Invalid JSON"
}
```
Invalid payload structure
`400 Bad Request`
```json
{
  "code": 400,
  "message": "Invalid event payload",
  "errors": {
    "payload.rule_id": "rule_id is required and must be a positive integer."
  }
}
```
## Best Practices for Integrators

- Always send ISO 8601 timestamps

- Ensure external_event_id is unique

- Use webhooks for notification delivery

- Retry requests if HTTP status is not 202

- Avoid sending duplicate events
