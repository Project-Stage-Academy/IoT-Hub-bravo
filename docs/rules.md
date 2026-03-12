# Rules & Events Documentation
 
## 1. Rule Object
 
The **Rule** model represents a business logic rule for monitoring and alerting.
 
| Field             | Type     | Required | Description                                |
| ----------------- | -------- | -------- | ------------------------------------------ |
| `id`              | integer  | auto     | Unique identifier of the rule              |
| `name`            | string   | Yes      | Rule name                                  |
| `description`     | string   | No       | Short description of the rule              |
| `is_active`       | boolean  | Yes      | Whether the rule is active                 |
| `condition`       | object   | Yes      | Trigger condition (JSON)                   |
| `action`          | object   | Yes      | Action performed when rule triggers (JSON) |
| `device_metric_id`| integer  | Yes      | Foreign key to DeviceMetric                |
| `created_at`      | datetime | auto     | Creation timestamp                         |
 
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
 
```json
{
  "type": "threshold",
  "operator": ">",
  "value": 30
}
```
 
**Supported operators:** `>`, `<`, `>=`, `<=`, `==`, `!=`
 
### 2.2 Rate Rule
 
Counts telemetry events over a sliding time window.
 
```json
{
  "type": "rate",
  "operator": ">=",
  "count": 5,
  "minutes": 1
}
```
 
The rule triggers if at least `count` telemetry events occurred within the last `minutes` minutes.
 
### 2.3 Composite Rule
 
Combines multiple rule conditions using logical operators.
 
```json
{
  "type": "composite",
  "operator": "AND",
  "conditions": [
    { "type": "threshold", "operator": ">", "value": 70 },
    { "type": "rate", "operator": ">=", "count": 3, "minutes": 2 }
  ]
}
```
 
**Supported operators:** `AND`, `OR`
 
- `AND` — all sub-conditions must evaluate to true
- `OR` — at least one sub-condition must evaluate to true
 
---
 
## 3. Rules API
 
All endpoints require JWT Bearer token in the `Authorization` header.
 
### 3.1 List Rules
 
```
GET /api/rules/?limit=20&offset=0
Authorization: Bearer <token>
```
 
**Query parameters:**
 
| Param    | Type | Default | Description              |
| -------- | ---- | ------- | ------------------------ |
| `limit`  | int  | 20      | Page size (must be > 0)  |
| `offset` | int  | 0       | Number of items to skip  |
 
**Response 200:**
 
```json
{
  "total": 2,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "name": "High Temperature Alert",
      "device_metric_id": 5,
      "description": "Alert when temperature exceeds 30",
      "condition": { "type": "threshold", "operator": ">", "value": 30 },
      "action": { "type": "notify", "message": "Temperature exceeded" },
      "is_active": true
    }
  ]
}
```
 
### 3.2 Get Rule by ID
 
```
GET /api/rules/1/
Authorization: Bearer <token>
```
 
**Response 200:**
 
```json
{
  "rule": {
    "id": 1,
    "name": "High Temperature Alert",
    "device_metric_id": 5,
    "description": "Alert when temperature exceeds 30",
    "condition": { "type": "threshold", "operator": ">", "value": 30 },
    "action": { "type": "notify", "message": "Temperature exceeded" },
    "is_active": true
  }
}
```
 
**Response 404:**
 
```json
{ "code": 404, "message": "Rule not found" }
```
 
### 3.3 Create Rule
 
```
POST /api/rules/
Authorization: Bearer <token>
Content-Type: application/json
```
 
**Request body:**
 
```json
{
  "schema_version": 1,
  "name": "High Temperature Alert",
  "description": "Alert when temperature exceeds 30",
  "condition": { "type": "threshold", "operator": ">", "value": 30 },
  "action": { "type": "notify", "message": "Temperature exceeded" },
  "is_active": true,
  "device_metric_id": 5
}
```
 
> `schema_version: 1` is required in all create/update/patch requests.
 
**Required fields:** `schema_version`, `name`, `condition`, `action`, `is_active`, `device_metric_id`
 
**Optional fields:** `description`
 
**Response 201:**
 
```json
{
  "id": 1,
  "name": "High Temperature Alert",
  "device_metric_id": 5,
  "description": "Alert when temperature exceeds 30",
  "condition": { "type": "threshold", "operator": ">", "value": 30 },
  "action": { "type": "notify", "message": "Temperature exceeded" },
  "is_active": true
}
```
 
### 3.4 Full Update (PUT)
 
```
PUT /api/rules/1/
Authorization: Bearer <token>
Content-Type: application/json
```
 
**Request body:** Same as Create (all required fields must be present).
 
**Response 200:** Updated rule object.
 
### 3.5 Partial Update (PATCH)
 
```
PATCH /api/rules/1/
Authorization: Bearer <token>
Content-Type: application/json
```
 
**Request body (only fields to update):**
 
```json
{
  "schema_version": 1,
  "is_active": false
}
```
 
> `schema_version: 1` is always required, even for PATCH.
 
**Response 200:**
 
```json
{ "status": 200, "rule_id": 1 }
```
 
### 3.6 Delete Rule
 
```
DELETE /api/rules/1/
Authorization: Bearer <token>
```
 
**Response 204:** Empty body.
 
### 3.7 Evaluate Rules
 
Evaluates all active rules against the latest telemetry for each device metric.
 
```
POST /api/rules/evaluate/
Authorization: Bearer <token>
Content-Type: application/json
```
 
**Request body (all fields optional):**
 
```json
{
  "device_id": 1,
  "device_metric_id": 5
}
```
 
- If `device_id` is provided, only rules for that device are evaluated.
- If `device_metric_id` is provided, only that specific metric is evaluated.
- If both are provided, the metric must belong to the device.
- If neither is provided, all rules for the user are evaluated.
 
**Response 200:**
 
```json
{
  "status": 200,
  "results": [
    {
      "telemetry_id": 42,
      "device_metric_id": 5,
      "device_name": "Sensor A",
      "result": [
        { "rule_id": 1, "rule_name": "High Temp", "triggered": true }
      ]
    }
  ]
}
```
 
---
 
## 4. Events API
 
Events are created automatically when a rule triggers during telemetry processing.
 
### 4.1 List Events
 
```
GET /api/events/?limit=50&offset=0
Authorization: Bearer <token>
```
 
**Query parameters:**
 
| Param          | Type | Default | Description                         |
| -------------- | ---- | ------- | ----------------------------------- |
| `limit`        | int  | 50      | Page size (max 200)                 |
| `offset`       | int  | 0       | Number of items to skip             |
| `rule_id`      | int  | —       | Filter by rule ID                   |
| `device_id`    | int  | —       | Filter by device ID                 |
| `acknowledged` | bool | —       | Filter by acknowledgement status    |
 
**Response 200:**
 
```json
{
  "count": 15,
  "limit": 50,
  "offset": 0,
  "results": [
    {
      "id": 1,
      "timestamp": "2026-03-10T12:05:0000:00",
      "created_at": "2026-03-10T12:05:0100:00",
      "acknowledged": false,
      "rule": {
        "id": 3,
        "name": "High Temperature Alert"
      }
    }
  ]
}
```
 
### 4.2 Get Event by ID
 
```
GET /api/events/1/
Authorization: Bearer <token>
```
 
**Response 200:**
 
```json
{
  "id": 1,
  "timestamp": "2026-03-10T12:05:0000:00",
  "created_at": "2026-03-10T12:05:0100:00",
  "acknowledged": false,
  "rule": {
    "id": 3,
    "name": "High Temperature Alert"
  }
}
```
 
**Response 404:**
 
```json
{ "detail": "Event not found." }
```
 
### 4.3 Acknowledge Event
 
```
POST /api/events/1/ack/
Authorization: Bearer <token>
```
 
No request body required.
 
**Response 200:** Returns the updated event object with `"acknowledged": true`.
 
---
 
## 5. Authorization Matrix
 
All rule/event endpoints require JWT authentication.
 
**Rules API**
 
| Endpoint                 | Method                    | Required Role  |
| ------------------------ | ------------------------- | -------------- |
| `/api/rules/`            | GET                       | client, admin  |
| `/api/rules/`            | POST                      | client, admin  |
| `/api/rules/{id}/`       | GET, PUT, PATCH, DELETE    | client, admin  |
| `/api/rules/evaluate/`   | POST                      | client, admin  |
 
**Events API**
 
| Endpoint                 | Method | Required Role  |
| ------------------------ | ------ | -------------- |
| `/api/events/`           | GET    | client, admin  |
| `/api/events/{id}/`      | GET    | client, admin  |
| `/api/events/{id}/ack/`  | POST   | client, admin  |
 
**Access control:** Non-admin users can only access rules and events for devices they own. Admin users can access all rules and events.
 
---
 
## 6. Admin Usage Guide
 
### Django Admin Panel
 
Access at `http://localhost:8000/admin/` (requires a superuser account).
 
**Rules management:**
- Create, edit, activate, or deactivate rules
- Filter rules by `is_active`, `device_metric`
- Search rules by name
 
**Events management:**
- View events with filters: `acknowledged`, `rule`, `created_at`
- Acknowledge events in bulk via admin actions
- Export events via the management command (see [export_events.md](export_events.md))
 
### Create a superuser
 
```bash
docker compose exec web python manage.py createsuperuser
```
 
---
 
## 7. Tutorials & Sample Workflows
 
> All examples assume you have a valid JWT token. Replace `<token>` with your actual token and adjust IDs for your data.
 
### 7.1 Create a Threshold Rule and Trigger an Event
 
```bash
# Step 1: Create a threshold rule for device_metric_id=5
curl -s -X POST http://localhost:8000/api/rules/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "name": "High Temperature",
    "description": "Triggers when temperature > 30",
    "condition": {"type": "threshold", "operator": ">", "value": 30},
    "action": {"type": "notify", "message": "Temperature exceeded 30"},
    "is_active": true,
    "device_metric_id": 5
  }'
 
# Step 2: Send telemetry with value > 30 via MQTT
mosquitto_pub -h localhost -p 1883 -t "telemetry" -m \
  '{"schema_version":1,"device":"SN-00001","metrics":{"temperature":{"value":35,"unit":"celsius"}},"ts":"2026-03-12T12:00:00Z"}'
 
# Step 3: Check events — a new event should appear
curl -s http://localhost:8000/api/events/ \
  -H "Authorization: Bearer <token>" | python3 -m json.tool
```
 
### 7.2 Create a Rate Rule
 
```bash
curl -s -X POST http://localhost:8000/api/rules/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "name": "Burst Detection",
    "description": "Triggers on 5 messages in 1 minute",
    "condition": {"type": "rate", "operator": ">=", "count": 5, "minutes": 1},
    "action": {"type": "notify", "message": "Message burst detected"},
    "is_active": true,
    "device_metric_id": 5
  }'
```
 
### 7.3 Create a Composite Rule (AND)
 
```bash
curl -s -X POST http://localhost:8000/api/rules/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "name": "Critical Alert",
    "description": "High temp AND burst",
    "condition": {
      "type": "composite",
      "operator": "AND",
      "conditions": [
        {"type": "threshold", "operator": ">", "value": 50},
        {"type": "rate", "operator": ">=", "count": 3, "minutes": 2}
      ]
    },
    "action": {"type": "notify", "message": "Critical condition detected"},
    "is_active": true,
    "device_metric_id": 5
  }'
```
 
### 7.4 List and Acknowledge Events
 
```bash
# List unacknowledged events
curl -s "http://localhost:8000/api/events/?acknowledged=false" \
  -H "Authorization: Bearer <token>" | python3 -m json.tool
 
# Acknowledge event with id=1
curl -s -X POST http://localhost:8000/api/events/1/ack/ \
  -H "Authorization: Bearer <token>"
```
 
### 7.5 Evaluate Rules Manually
 
```bash
# Evaluate all rules for a specific device
curl -s -X POST http://localhost:8000/api/rules/evaluate/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"device_id": 1}'
 
# Evaluate rules for a specific device_metric
curl -s -X POST http://localhost:8000/api/rules/evaluate/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"device_metric_id": 5}'
```
 
---
 
## 8. FAQ & Troubleshooting
 
**Q: My rule is not triggering. What should I check?**
- Is the rule `is_active: true`?
- Does the `device_metric_id` match the metric receiving telemetry?
- Does the condition match the incoming value? (e.g., `>` vs `>=`)
- Is the Celery worker running? (`docker compose logs worker`)
 
**Q: Events are not appearing after rule creation.**
- Events are created during telemetry processing, not during rule creation.
- Ensure new telemetry is being sent after the rule is created.
- Check the Celery worker logs for rule evaluation errors.
 
**Q: How do I test rules locally?**
- Use the curl examples in Section 7.
- Send telemetry via MQTT: `mosquitto_pub -h localhost -p 1883 -t "telemetry" -m '<json>'`
- Check events via API: `GET /api/events/`
 
**Q: How do I monitor rule processing?**
- Open the Grafana dashboard at `http://localhost:3000`
- See the "Rules Processing" panel for evaluation/trigger rates.
- Check Prometheus at `http://localhost:9090` for `iot_rules_evaluated_total` and `iot_rules_triggered_total` metrics.
 
**Q: What is the default time window for rate rules?**
- The time window is defined in the rule condition via the `minutes` field.
- There is no global default; each rule specifies its own window.
 
**Q: How do I export events?**
- Use the management command: `python manage.py export_events`
- See [export_events.md](export_events.md) for full documentation.
 
**Q: How to deactivate a rule without deleting it?**
 
```bash
curl -s -X PATCH http://localhost:8000/api/rules/1/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"schema_version": 1, "is_active": false}'
```
 
---
 
## Related Documentation
 
- [OpenAPI Specification](api.yaml) — Swagger/OpenAPI 3.0.3 spec (view at `http://localhost:5433`)
- [API Authentication & Style Guide](api-guide.md) — Auth, JWT, pagination conventions
- [Export Events](export_events.md) — Management command for exporting events
- [Alerting & Monitoring](alerting.md) — Prometheus metrics and Grafana dashboards