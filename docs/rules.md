# Rules Documentation

## 1. Rule Object

The **Rule** model represents a business logic rule for monitoring and alerting.

| Field           | Type     | Description                                |
| --------------- | -------- | ------------------------------------------ |
| `id`            | UUID     | Unique identifier of the rule              |
| `name`          | string   | Rule name                                  |
| `description`   | string   | Short description of the rule              |
| `is_active`     | boolean  | Whether the rule is active                 |
| `condition`     | object   | Trigger condition (JSON)                   |
| `action`        | object   | Action performed when rule triggers (JSON) |
| `device_metric` | UUID     | Foreign key to DeviceMetric                |
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

## 2. CRUD Operations

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
  "device_metric": "123e4567-e89b-12d3-a456-426614174000"
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

## 3. Event Schema

When a rule triggers, an **Event** is generated:

```json
{
  "id": "event-uuid",
  "rule": "550e8400-e29b-41d4-a716-446655440000",
  "device_metric": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2026-02-09T10:05:00Z",
  "trigger_telemetry": "550e8400-e29b-41d4-a716-446655440000",
}
```

**Field explanations:**

* `rule_id` — the rule that triggered the event
* `device_metric` — metric associated with the rule
* `value` — metric value that caused the trigger
* `trigger_telemetry` — which tele
