# Rule Engine: Action Definitions

This document outlines the structure and supported types of actions that can be executed when an IoT Rule is triggered. 

The `action` field in the `Rule` model uses a flexible JSON format. The system processes these actions asynchronously using an Event-Driven Architecture (Kafka -> PostgreSQL -> Celery) ensuring reliable delivery with retry mechanisms.

## Supported Action Types

Currently, the system supports configuring multiple actions simultaneously within a single rule.

### 1. Email Notification (`notification`)
Sends an email alert to a specified recipient with details about the triggered rule and telemetry context.

**JSON Configuration:**
```json
{
  "notification": {
    "enabled": true,
    "channel": "email",
    "recipient": "admin@example.com",
    "subject": "Critical Alert: High Temperature Detected",
    "message": "The temperature in Server Room 1 has exceeded the safe threshold."
  }
}
```

### 2. Webhook Delivery (webhook)
Sends an HTTP POST request with the full event payload (including trigger_context) to an external URL. Useful for integrating with third-party systems like Slack, PagerDuty, or custom dashboards.

**JSON Configuration:**
```json
{
  "webhook": {
    "enabled": true,
    "url": "[https://api.thirdparty.com/v1/iot-alerts](https://api.thirdparty.com/v1/iot-alerts)"
  }
}
```
### Combined Action Example
You can mix and match actions. If a rule triggers, the system will independently dispatch both an email and a webhook, tracking their delivery statuses separately.
```json
{
  "notification": {
    "enabled": true,
    "channel": "email",
    "recipient": "oncall@iot-hub.local",
    "subject": "Pressure Drop Alert",
    "message": "Immediate attention required."
  },
  "webhook": {
    "enabled": true,
    "url": "[https://webhook.site/your-unique-id](https://webhook.site/your-unique-id)"
  }
}
```
### Traceability & Delivery Handling
All triggered actions are recorded in the event_deliveries database table.

- Traceability: You can track the exact payload, target, and status (PENDING, PROCESSING, SUCCESS, REJECTED) via the Django Admin interface.

- Error Handling: If a webhook endpoint is down or an email server times out, the system automatically applies Exponential Backoff retries (up to 5 attempts).

- Fault Tolerance: If the worker crashes, a periodic Sweeper task automatically recovers stuck deliveries, guaranteeing At-Least-Once delivery.

