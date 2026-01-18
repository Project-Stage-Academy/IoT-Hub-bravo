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
- Foreign key index on `user_id`

**Relationships:**
- `user_id` → `users.id` (ON DELETE SET NULL)

**Note:** Future fields may include `location` (JSONB) and `last_seen` (TIMESTAMP).

---

### metrics

Defines available metric types that can be collected from devices.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique metric identifier |
| metric_type | VARCHAR(100) | UNIQUE | Type name (e.g., 'temperature', 'humidity', 'pressure') |

**Indexes:**
- Primary key on `id`
- Unique index on `metric_type`

**Note:** Future fields may include `data_type` ENUM('integer', 'float', 'string', 'boolean', 'json').

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
- Unique composite index on `(device_id, metric_id)`

**Relationships:**
- `device_id` → `devices.id` (ON DELETE SET NULL)
- `metric_id` → `metrics.id` (ON DELETE SET NULL)

---

### telemetries

Stores time-series telemetry data collected from devices.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique telemetry record identifier |
| value | NUMERIC | NULL | Telemetry value |
| timestamp | TIMESTAMP | NOT NULL | When the measurement was taken |
| device_metric_id | INTEGER | NULL, FOREIGN KEY | Reference to device-metric combination (references device_metrics.id) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Indexes:**
- Primary key on `id`
- Foreign key index on `device_metric_id`
- **Recommended:** Index on `timestamp` for time-series queries
- **Recommended:** Composite index on `(device_metric_id, timestamp)` for efficient filtering

**Relationships:**
- `device_metric_id` → `device_metrics.id` (ON DELETE SET NULL)

**Note:** Future fields may include direct `device_id` and `metric_type` for denormalization.

---

### rules

Defines business rules that react to telemetry conditions and trigger actions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY, AUTO INCREMENT | Unique rule identifier |
| name | VARCHAR(255) | NOT NULL | Rule display name |
| description | TEXT | NULL | Rule description |
| condition | JSONB | NOT NULL | Rule condition logic (e.g., {"metric": "temperature", "operator": ">", "value": 30}) |
| action | JSONB | NOT NULL | Action to execute when condition is met (e.g., {"type": "alert", "target": "email"}) |
| device_id | INTEGER | NULL, FOREIGN KEY | Device this rule applies to (references devices.id) |
| device_metric_id | INTEGER | NULL, FOREIGN KEY | Specific device-metric combination (references device_metrics.id) |
| is_active | BOOLEAN | DEFAULT TRUE | Rule active status |

**Indexes:**
- Primary key on `id`
- Foreign key index on `device_id`
- Foreign key index on `device_metric_id`
- **Recommended:** Index on `is_active` for filtering active rules

**Relationships:**
- `device_id` → `devices.id` (ON DELETE CASCADE)
- `device_metric_id` → `device_metrics.id` (ON DELETE SET NULL)

**Note:** Future fields may include `priority` (INTEGER) and timestamps.

---

### events

Stores events generated when rules are triggered or other system events occur.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGSERIAL | PRIMARY KEY, AUTO INCREMENT | Unique event identifier |
| timestamp | TIMESTAMP | NOT NULL | Event occurrence time |
| device_id | INTEGER | NULL, FOREIGN KEY | Device that generated the event (references devices.id) |
| rule_id | INTEGER | NULL, FOREIGN KEY | Rule that triggered this event (references rules.id) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Indexes:**
- Primary key on `id`
- Index on `timestamp` (idx_events_timestamp) - **critical for time-series queries**
- Index on `device_id` (idx_events_device_id) - **critical for device-specific queries**
- Foreign key index on `rule_id`

**Relationships:**
- `device_id` → `devices.id` (ON DELETE CASCADE)
- `rule_id` → `rules.id` (ON DELETE SET NULL)

**Note:** Future fields may include `payload` (JSONB), `event` (VARCHAR(100)), and `processed` (BOOLEAN).

---

## Entity Relationship Summary

```
users (1) ──< (many) devices
devices (1) ──< (many) device_metrics ──> (many) metrics
device_metrics (1) ──< (many) telemetries
device_metrics (1) ──< (many) rules
devices (1) ──< (many) rules
devices (1) ──< (many) events
rules (1) ──< (many) events
```

## Primary Key Recommendations

All tables use `SERIAL` or `BIGSERIAL` auto-incrementing integers as primary keys:
- `users.id` - SERIAL
- `devices.id` - SERIAL
- `metrics.id` - SERIAL
- `device_metrics.id` - SERIAL
- `telemetries.id` - SERIAL
- `rules.id` - SERIAL
- `events.id` - BIGSERIAL (for high-volume event storage)

## Index Recommendations

### Critical Indexes (Already Defined)
- Unique constraints on `users.username`, `users.email`
- Unique constraint on `devices.serial_id`
- Unique constraint on `metrics.metric_type`
- Unique composite index on `device_metrics(device_id, metric_id)`
- Index on `events.timestamp` (idx_events_timestamp)
- Index on `events.device_id` (idx_events_device_id)

### Recommended Additional Indexes
- `telemetries.timestamp` - For time-range queries
- `telemetries(device_metric_id, timestamp)` - Composite index for efficient filtering
- `rules.is_active` - For filtering active rules
- `devices.user_id` - For user device listings
- `devices.is_active` - For filtering active devices

## Future Schema Considerations

The following tables and fields are planned but not yet implemented:

### notifications
- Stores notification records for events
- Links to events table
- Supports multiple notification types (email, webhook, SMS)

### audit_logs
- Tracks user actions and system changes
- Links to users table
- Stores action details in JSONB format

### Additional Fields
- Device location tracking (JSONB)
- Device last seen timestamp
- Rule priority levels
- Event payload storage
- Event type classification
- Event processing status
