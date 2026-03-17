# Rules Documentation

## 1. Rule Object

The **Rule** model represents a business logic rule for monitoring and alerting.

| Field           | Type     | Required | Description                                |
| --------------- | -------- | -------- | ------------------------------------------ |
| `id`            | integer  | Yes      | Unique identifier of the rule              |
| `name`          | string   | Yes      | Rule name                                  |
| `description`   | string   | No       | Short description of the rule              |
| `is_active`     | boolean  | Yes      | Whether the rule is active                 |
| `condition`     | object   | Yes      | Trigger condition (JSON)                   |
| `action`        | object   | Yes      | Action performed when rule triggers (JSON) |
| `device_metric` | integer  | Yes      | Foreign key to DeviceMetric                |
| `created_at`    | datetime | Yes      | Creation timestamp                         |


**Example `condition`:**

```json
{
  "type": "threshold",
  "operator": ">",
  "value": 30
}
```

**Example `action`:**

```json
{
  "webhook": {
    "url": "https://webhook.site/a6bf3275-595d-42fd-b759-c42d74ce8c9e",
    "enabled": true
  },
  "notification": {
    "channel": "email",
    "enabled": true,
    "message": "High temperature in {device_name}: {value}°C"
  }
}
```

---
## 2. Rule Expression Contract

The `condition` field defines a rule expression in JSON format.
Rule expressions are evaluated against incoming telemetry values.
If a rule condition is invalid or unsupported, the rule does not trigger and evaluation returns `false`.

### 2.1 Threshold Rule

Compares a telemetry value against a static threshold.

**Example:**
```json
{
  "type": "threshold",
  "operator": ">",
  "value": 30
}
```

**Supported operators for threshold:** `>`, `<`, `>=`, `<=`, `==`, `!=`
**Supported operators for composite:** `AND`, `OR`

---

### 2.2 Rate Rule

Counts telemetry events over a sliding time window.

**Example:**

```json
{
  "type": "rate",
  "operator": ">=",
  "count": 5,
  "duration_minutes": 1
}
```

**Description:**
The rule triggers if at least 5 telemetry events occurred within the last 1 minute.

---

### 2.3 Composite Rule

Combines multiple rule conditions using logical operators.

**Example:**

```json
{
  "type": "composite",
  "operator": "AND",
  "conditions": [
    {
      "type": "threshold",
      "operator": ">",
      "value": 70
    },
    {
      "type": "rate",
      "operator": ">=",
      "count": 3,
      "minutes": 2
    }
  ]
}
```

**Supported operators:** `AND`, `OR`

> The rule triggers depending on the logical operator:
>
> * `AND` — all sub-conditions must evaluate to true
> * `OR` — at least one sub-condition must evaluate to true

---
## 3.1 CRUD Operations

### Create Rule

**POST /rules**

**Request Body:**

```json
{
  "name": "High Temperature Alert",
  "description": "Alert when temperature exceeds 30°C",
  "is_active": true,
  "condition": {
    "type": "threshold",
    "value": 13,
    "operator": ">"
  },
  "action": {
    "webhook": {
      "url": "https://webhook.site/a6bf3275-595d-42fd-b759-c42d74ce8c9e",
      "enabled": true
    },
    "notification": {
      "channel": "email",
      "enabled": true,
      "message": "High temperature in {device_name}: {value}°C"
    }
  },
  "device_metric": 123
}
```

**Response Body:**
Full Rule object including `id` and `created_at`.

---

### Update Rule

**PUT /rules/{id}** — full update rule fields.

**PATCH /rules/{id}** — partially update rule fields.

---

### Delete Rule

**DELETE /rules/{id}** — delete rule.

---

## 3.2 Constraints and Validation

### Unique Rule Name per Device Metric

* Each `(device_metric, name)` pair must be **unique**.
* Attempting to create a rule with the same `name` for the same `device_metric` returns:

```json
{
  "code": 400,
  "message": "Rule with this name already exists for this device_metric."
}
```

* This is enforced both in the database via a **unique constraint** and in the API via validation to prevent `IntegrityError`.
* This ensures **idempotency**: repeated requests with the same `name` and `device_metric` will not create duplicates and will provide a clear client error instead of a 500.

**Rationale:**
Preventing duplicate rules avoids conflicting triggers for the same metric, simplifies client logic, and improves system reliability.


## 4. Event Schema

When a rule triggers, an **Event** is generated:

```json
{
  "id": 123,
  "rule_id": 456,
  "timestamp": "2026-02-09T10:05:00Z",
  "acknowledged": false,
  "created_at": "2026-02-09T10:05:10Z",
  "trigger_telemetry_id": 123,
}
```

**Field explanations:**

| Field          | Type     | Description                                        |
| -------------- | -------- | -------------------------------------------------- |
| `id`           | integer  | Unique identifier of the event                     |
| `rule_id`      | integer  | Reference to the rule that triggered the event     |
| `timestamp`    | datetime | When the event occurred (evaluated telemetry time) |
| `acknowledged` | boolean  | Whether the event was acknowledged                 |
| `created_at`   | datetime | When the event record was created in the database  |
| `trigger_telemetry_id`   | int | Which telemtry trigger the event  |


