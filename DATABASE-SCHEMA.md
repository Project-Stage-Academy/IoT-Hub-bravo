# Database Schema Documentation

This document describes the database schema for the IoT Catalog Hub application.

## Overview

The database consists of core tables for user management, device registration, telemetry collection, rule evaluation, and event tracking.

## Tables

### users

Stores user account information and authentication data.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique user identifier |
| username | VARCHAR(150) | UNIQUE, NOT NULL | User login name |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| password | VARCHAR(255) | NOT NULL | Hashed password |
| role | ENUM('admin', 'client') | DEFAULT 'client' | User role in the system |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `username`
- Unique index on `email`
- Index on `role` (idx_users_role)

---

### devices

Stores registered IoT devices and their metadata.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique device identifier |
| serial_id | VARCHAR(255) | UNIQUE, NOT NULL | Device serial number |
| name | VARCHAR(255) | NOT NULL | Device display name |
| description | TEXT | NULL | Device description |
| user_id | INTEGER | NULL, FOREIGN KEY | Owner of the device (references users.id) |
| is_active | BOOLEAN | DEFAULT TRUE | Device active status |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Device registration timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `serial_id`
- Index on `user_id` (idx_devices_user_id)
- Index on `is_active` (idx_devices_is_active)

**Relationships:**
- `user_id` → `users.id` (ON DELETE CASCADE)

---

### metrics

Defines available metric types that can be collected from devices.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique metric identifier |
| metric_type | CITEXT | UNIQUE, NOT NULL | Type name (e.g., 'temperature', 'humidity', 'pressure') - case-insensitive |
| data_type | ENUM('numeric', 'str', 'bool') | NOT NULL | Data type of the metric value |

**Indexes:**
- Primary key on `id`
- Unique index on `metric_type` (case-insensitive due to CITEXT)

---

### device_metrics

Junction table linking devices to their available metrics (many-to-many relationship).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique junction identifier |
| device_id | INTEGER | NOT NULL, FOREIGN KEY | Device reference (references devices.id) |
| metric_id | INTEGER | NOT NULL, FOREIGN KEY | Metric reference (references metrics.id) |

**Indexes:**
- Primary key on `id`
- Unique composite index on `(device_id, metric_id)` (uq_device_metric)
- Index on `device_id` (idx_device_metrics_device)
- Index on `metric_id` (idx_device_metrics_metric)

**Relationships:**
- `device_id` → `devices.id` (ON DELETE CASCADE)
- `metric_id` → `metrics.id` (ON DELETE RESTRICT)

---

### telemetries

Stores time-series telemetry data collected from devices. Uses JSONB for flexible value storage with generated columns for type-specific access.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGSERIAL | PRIMARY KEY, AUTO INCREMENT | Unique telemetry record identifier |
| device_metric_id | INTEGER | NOT NULL, FOREIGN KEY | Reference to device-metric combination (references device_metrics.id) |
| value_jsonb | JSONB | NOT NULL | Telemetry value stored as JSONB with structure: `{"t": "type", "v": "value"}` |
| value_numeric | NUMERIC | GENERATED ALWAYS AS STORED | Generated column for numeric values (when value_jsonb->>'t' = 'numeric') |
| value_bool | BOOLEAN | GENERATED ALWAYS AS STORED | Generated column for boolean values (when value_jsonb->>'t' = 'bool') |
| value_str | TEXT | GENERATED ALWAYS AS STORED | Generated column for string values (when value_jsonb->>'t' = 'str') |
| ts | TIMESTAMPTZ | NOT NULL, DEFAULT now() | When the measurement was taken |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation timestamp |

**Indexes:**
- Primary key on `id`
- Unique composite index on `(device_metric_id, ts)` (unique_telemetry_per_metric_time)
- Composite index on `(device_metric_id, ts)` (idx_telemetries_metric_time)
- Index on `ts` (idx_telemetries_timestamp)

**Relationships:**
- `device_metric_id` → `device_metrics.id` (ON DELETE CASCADE)

**Note:** The `value_jsonb` field stores values in the format `{"t": "numeric|str|bool", "v": <actual_value>}`. Generated columns provide type-safe access to values based on the type indicator.

---

### rules

Defines business rules that react to telemetry conditions and trigger actions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique rule identifier |
| name | VARCHAR(255) | NOT NULL | Rule display name |
| description | TEXT | NULL | Rule description |
| condition | JSONB | NOT NULL | Rule condition logic (e.g., {"operator": ">", "value": 30}) |
| action | JSONB | NOT NULL | Action to execute when condition is met (e.g., {"type": "alert", "target": "email"}) |
| device_metric_id | INTEGER | NULL, FOREIGN KEY | Specific device-metric combination this rule applies to (references device_metrics.id) |
| is_active | BOOLEAN | DEFAULT TRUE | Rule active status |

**Indexes:**
- Primary key on `id`
- Index on `device_metric_id` (idx_rules_device_metric)
- Index on `is_active` (idx_rules_is_active)

**Relationships:**
- `device_metric_id` → `device_metrics.id` (ON DELETE CASCADE)

---

### events

Stores events generated when rules are triggered or other system events occur.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGSERIAL | PRIMARY KEY, AUTO INCREMENT | Unique event identifier |
| timestamp | TIMESTAMP | NOT NULL | Event occurrence time |
| rule_id | INTEGER | NULL, FOREIGN KEY | Rule that triggered this event (references rules.id) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Indexes:**
- Primary key on `id`
- Index on `timestamp` (idx_events_timestamp)
- Index on `rule_id` (idx_events_rule)

**Relationships:**
- `rule_id` → `rules.id` (ON DELETE CASCADE)

---

## Entity Relationship Summary

```
users (1) ──< (many) devices
devices (1) ──< (many) device_metrics ──> (many) metrics
device_metrics (1) ──< (many) telemetries
device_metrics (1) ──< (many) rules
rules (1) ──< (many) events
```

## Foreign Key Relationships

| From Table | From Column | To Table | To Column | Delete Action |
|-----------|-------------|----------|-----------|---------------|
| devices | user_id | users | id | CASCADE |
| device_metrics | device_id | devices | id | CASCADE |
| device_metrics | metric_id | metrics | id | RESTRICT |
| telemetries | device_metric_id | device_metrics | id | CASCADE |
| rules | device_metric_id | device_metrics | id | CASCADE |
| events | rule_id | rules | id | CASCADE |

## Key Design Decisions

1. **Telemetry Value Storage**: Uses JSONB with generated columns to support multiple data types (numeric, string, boolean) while maintaining type safety and query performance.

2. **Case-Insensitive Metric Types**: The `metric_type` field uses CITEXT to prevent duplicate metric types with different cases (e.g., "Temperature" vs "temperature").

3. **Cascade Deletes**: Most relationships use CASCADE to maintain referential integrity and prevent orphaned records. The exception is `metrics` → `device_metrics` which uses RESTRICT to prevent accidental deletion of metrics that are in use.

4. **Time-Series Optimization**: The `telemetries` table uses BIGSERIAL for high-volume data and includes composite indexes on `(device_metric_id, ts)` for efficient time-range queries.

5. **Rule Evaluation**: Rules are linked to specific `device_metric_id` combinations, allowing fine-grained control over which telemetry data triggers which rules.

## Future Considerations

The following table is planned but not yet implemented:

### notifications
- Stores notification records for events
- Links to events table
- Supports multiple notification types (email, webhook, SMS)
- Tracks notification status and delivery timestamps
