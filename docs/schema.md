
### Database Schema

```mermaid
erDiagram
    USERS ||--o{ DEVICES          : "owns"
    DEVICES ||--o{ DEVICE_METRICS : "has"
    METRICS ||--o{ DEVICE_METRICS : "is measured on"
    DEVICE_METRICS ||--o{ TELEMETRIES     : "records"
    DEVICE_METRICS ||--o{ RULES           : "triggers"
    RULES          ||--o{ EVENTS          : "generates"

    USERS {
        int      id          PK "serial, auto-increment"
        varchar  username    UK "unique, not null, max 150"
        varchar  email       UK "unique, not null, max 255"
        varchar  password    "not null, max 255"
        enum     role        "admin / client, default: client"
        timestamp created_at "default: CURRENT_TIMESTAMP"
        timestamp updated_at "default: CURRENT_TIMESTAMP"
    }

    DEVICES {
        int      id          PK "serial, auto-increment"
        varchar  serial_id   UK "unique, not null, max 255"
        varchar  name        "not null, max 255"
        text     description
        int      user_id     FK "references users"
        boolean  is_active   "default: true"
        timestamp created_at "default: CURRENT_TIMESTAMP"
    }

    METRICS {
        int    id         PK "serial, auto-increment"
        citext metric_type UK "unique, not null"
        enum   data_type   "numeric / str / boolean, not null"
    }

    DEVICE_METRICS {
        int id          PK "serial, auto-increment"
        int device_id   FK "→ devices.id"
        int metric_id   FK "→ metrics.id"
    }

    TELEMETRIES {
        bigint      id               PK "bigserial, auto-increment"
        int         device_metric_id FK "→ device_metrics.id"
        jsonb       value_jsonb      "not null"
        numeric     value_numeric    "GENERATED ALWAYS AS ..."
        boolean     value_bool       "GENERATED ALWAYS AS ..."
        text        value_str        "GENERATED ALWAYS AS ..."
        timestamptz ts               "not null, default: now()"
        timestamptz created_at       "default: now()"
    }

    RULES {
        int     id                PK "serial, auto-increment"
        varchar name              "not null, max 255"
        text    description
        jsonb   condition         "not null"
        jsonb   action            "not null"
        boolean is_active         "default: true"
        int     device_metric_id  FK "→ device_metrics.id, not null"
    }

    EVENTS {
        bigint    id         PK "bigserial, auto-increment"
        timestamp timestamp
        int       rule_id    FK "→ rules.id, not null"
        timestamp created_at "default: CURRENT_TIMESTAMP, not null"
    }
```

## Recommended Indexes

| Table            | Index name                          | Columns                          | Type       | Purpose / Accelerated queries                                      |
|------------------|-------------------------------------|----------------------------------|------------|--------------------------------------------------------------------|
| users            | idx_users_role                      | role                             | normal     | Filtering by role (admin vs client)                                |
| devices          | idx_devices_user_id                 | user_id                          | normal     | Fast lookup of devices per user                                    |
| devices          | idx_devices_is_active               | is_active                        | normal     | Filtering active/inactive devices                                  |
| device_metrics   | uq_device_metric                    | device_id, metric_id             | **unique** | Prevent duplicate metric assignments per device                    |
| device_metrics   | idx_device_metrics_device           | device_id                        | normal     | Quick access to all metrics of a device                            |
| device_metrics   | idx_device_metrics_metric           | metric_id                        | normal     | Quick access to devices measuring a specific metric                |
| rules            | idx_rules_device_metric             | device_metric_id                 | normal     | Find rules for specific device+metric                              |
| rules            | idx_rules_is_active                 | is_active                        | normal     | Filter active rules quickly                                        |
| events           | idx_events_timestamp                | timestamp                        | normal     | Time-range queries, sorting events by time                         |
| events           | idx_events_rule                     | rule_id                          | normal     | Find all events triggered by a rule                                |
| telemetries      | unique_telemetry_per_metric_time    | device_metric_id, ts             | **unique** | Prevent duplicate measurements at same timestamp                   |
| telemetries      | idx_telemetries_metric_time         | device_metric_id, ts             | normal     | Fast time-series queries per metric (most frequent access pattern) |
| telemetries      | idx_telemetries_timestamp           | ts                               | normal     | Global time-range queries across all telemetry                     |


# DBML LINK
https://dbdiagram.io/d/IoT-db-696d114dd6e030a0245f8e22
