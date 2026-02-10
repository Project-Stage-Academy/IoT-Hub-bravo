# Rules Documentation

## 1. Rule Object

The **Rule** model represents a business logic rule for monitoring and alerting.

| Field           | Type     | Description                                |
| --------------- | -------- | ------------------------------------------ |
| `id`            | integer     | Unique identifier of the rule              |
| `name`          | string   | Rule name                                  |
| `description`   | string   | Short description of the rule              |
| `is_active`     | boolean  | Whether the rule is active                 |
| `condition`     | object   | Trigger condition (JSON)                   |
| `action`        | object   | Action performed when rule triggers (JSON) |
| `device_metric` | integer    | Foreign key to DeviceMetric                |
| `created_at`    | datetime | Creation timestamp                         |

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
  "type": "notify",
  "message": "Temperature exceeded threshold"
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
````

**Supported operators:** `>`, `<`, `>=`, `<=`, `==`, `!=`

---

### 2.2 Rate Rule

Counts telemetry events over a sliding time window.

**Example:**

```json
{
  "type": "rate",
  "operator": ">=",
  "count": 5,
  "window_seconds": 60
}
```

**Description:**
The rule triggers if at least 5 telemetry events occurred within the last 60 seconds.

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
      "window_seconds": 120
    }
  ]
}
```

**Supported operators:** `AND`, `OR`

The rule triggers if all sub-conditions evaluate to true.

---
## 3. CRUD Operations

### Create Rule

**POST /rules**

**Request Body:**

```json
{
  "name": "High Temperature Alert",
  "description": "Alert when temperature exceeds 30°C",
  "is_active": true,
  "condition": { "type": "threshold", "operator": ">", "value": 30 },
  "action": { "type": "notify", "message": "Temperature exceeded threshold" },
  "device_metric": 123
}
```

**Response Body:**
Full Rule object including `id` and `created_at`.

---

### Update Rule

**PUT /rules/{id}** — update rule fields.

---

### Delete Rule

**DELETE /rules/{id}** — delete rule.

---

### Enable/Disable Rule

**PATCH /rules/{id}/enable**

```json
{ "is_active": true }
```

**PATCH /rules/{id}/disable**

```json
{ "is_active": false }
```

---

## 4. Event Schema

When a rule triggers, an **Event** is generated:

```json
{
  "id": "event-uuid",
  "rule": 123,
  "device_metric": 123,
  "created_at": "2026-02-09T10:05:00Z",
  "trigger_telemetry": 123,
}
```

**Field explanations:**

* `rule_id` — the rule that triggered the event
* `device_metric` — metric associated with the rule
* `value` — metric value that caused the trigger
* `trigger_telemetry` — which tele
