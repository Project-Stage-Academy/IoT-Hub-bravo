# Admin Permissions and Roles

## Overview

This document describes the admin permission roles and their capabilities in the IoT Hub system.

## Role Definitions

### 1. Admin (Superuser)

**Django Settings:** `is_superuser=True`, `is_staff=True`

**Capabilities:**
- Full access to all admin functionality
- Create, read, update, delete all models
- Manage users and permissions
- Execute all admin actions (enable/disable devices, export CSV, acknowledge events)
- Access Django admin settings

### 2. Operator

**Django Settings:** `is_superuser=False`, `is_staff=True`

**Permissions:**
- `devices.view_device`, `devices.change_device`
- `devices.view_telemetry`
- `devices.view_metric`, `devices.view_devicemetric`
- `rules.view_rule`, `rules.change_rule`
- `rules.view_event`, `rules.change_event`

**Capabilities:**
- View and modify devices (enable/disable)
- View telemetry data and export to CSV
- View and modify rules (activate/deactivate)
- View and acknowledge events
- Cannot create or delete records
- Cannot manage users

### 3. Viewer (Read-Only)

**Django Settings:** `is_superuser=False`, `is_staff=True`

**Permissions:**
- `devices.view_device`
- `devices.view_telemetry`
- `devices.view_metric`, `devices.view_devicemetric`
- `rules.view_rule`
- `rules.view_event`

**Capabilities:**
- View all devices and their telemetry
- View rules and events
- Cannot modify any data
- Cannot execute admin actions
- Cannot export data

## Permission Matrix

| Action                     | Admin | Operator | Viewer |
|----------------------------|-------|----------|--------|
| View devices               | ✅    | ✅       | ✅     |
| Create/delete devices      | ✅    | ❌       | ❌     |
| Enable/disable devices     | ✅    | ✅       | ❌     |
| View telemetry             | ✅    | ✅       | ✅     |
| Export telemetry to CSV    | ✅    | ✅       | ❌     |
| View rules                 | ✅    | ✅       | ✅     |
| Create/edit rules          | ✅    | ✅       | ❌     |
| Delete rules               | ✅    | ❌       | ❌     |
| View events                | ✅    | ✅       | ✅     |
| Acknowledge events         | ✅    | ✅       | ❌     |
| Manage users               | ✅    | ❌       | ❌     |

## Creating Roles via Django Admin

1. Go to **Authentication and Authorization > Groups**
2. Create groups: `Operators`, `Viewers`
3. Assign permissions as listed above
4. Add users to appropriate groups

## Creating Roles via Management Command

```bash
python manage.py create_admin_groups
