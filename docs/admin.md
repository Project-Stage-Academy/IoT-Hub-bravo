# IoT Hub - Django Admin Guide

This guide describes how to use the Django Admin interface to manage IoT devices, telemetry data, rules, and events.

## Table of Contents

- [Access & Authentication](#access--authentication)
- [User Roles & Permissions](#user-roles--permissions)
- [Common Workflows](#common-workflows)
  - [Managing Devices](#managing-devices)
  - [Viewing Telemetry Data](#viewing-telemetry-data)
  - [Creating and Managing Rules](#creating-and-managing-rules)
  - [Inspecting Events](#inspecting-events)
  - [Managing Metrics](#managing-metrics)
- [Admin Actions](#admin-actions)
- [Troubleshooting](#troubleshooting)

---

## Access & Authentication

**Admin Panel URL:** `http://localhost:8000/admin/`

### Default Users

| Username | Password | Role | Use Case |
|----------|----------|------|----------|
| `admin_from_script` | `admin123` | Superuser | System administration |
| `admin_user` | `admin123` | Admin | Full IoT data management |
| `operator_user` | `operator123` | Operator | Day-to-day operations |
| `viewer_user` | `viewer123` | Viewer | Read-only monitoring |

### Login Steps

1. Navigate to `http://localhost:8000/admin/`
2. Enter username and password
3. Click "Log in"
4. You'll see the admin dashboard with available models

---

## User Roles & Permissions

### 🔴 Superuser
- **Full system access**
- Can create/delete users
- Can modify all settings
- Access to Django admin configuration

### 🟠 Admin
- **Full CRUD on all IoT models**
- View, Add, Change, Delete: Devices, Telemetry, Metrics, Rules, Events
- Bulk operations
- Export data

### 🟡 Operator
- **View, Add, Change (no Delete)**
- Can create new devices and rules
- Can modify existing data
- Cannot delete any records

### 🟢 Viewer
- **Read-only access**
- View all data
- Export to CSV
- Cannot modify anything

---

## Common Workflows

### Managing Devices

#### 1. Create a New Device

**Steps:**
1. Log in as `admin_user` or `operator_user`
2. Click on **"Devices"** in the left sidebar
3. Click **"Add Device"** button (top right)
4. Fill in the form:
   - **Serial ID**: Unique identifier (e.g., `SN-20240001`)
   - **Name**: Human-readable name (e.g., `Temperature Sensor - Room 101`)
   - **Description**: Optional description
   - **User**: Select the owner user
   - **Is Active**: Check to activate device
5. Click **"Save"**



#### 2. View All Devices

**Steps:**
1. Click **"Devices"** in sidebar
2. You'll see a list with columns:
   - ID
   - Serial ID
   - Name
   - User (owner)
   - Is Active
   - Created At

**Filtering:**
- Use the right sidebar to filter by:
  - Active status
  - Creation date

**Search:**
- Use the search box to find devices by:
  - Serial ID
  - Name
  - Username

#### 3. Edit a Device

**Steps:**
1. Go to Devices list
2. Click on the device name or ID
3. Modify fields as needed
4. Click **"Save"** or **"Save and continue editing"**

#### 4. Deactivate a Device

**Steps:**
1. Go to Devices list
2. Click on the device
3. Uncheck **"Is Active"**
4. Click **"Save"**

**Bulk Deactivation:**
1. Go to Devices list
2. Select multiple devices (checkboxes)
3. Select action **"Deactivate selected devices"** (if available)
4. Click **"Go"**

---

### Viewing Telemetry Data

#### 1. View Recent Telemetry for a Device

**Steps:**
1. Click **"Telemetry"** in sidebar
2. Use search to find device name
3. Or use filter by date range (right sidebar)
4. Click on a telemetry record to see details:
   - Device Metric (device + metric type)
   - Value (JSON format)
   - Timestamp
   - Created At


#### 2. Filter Telemetry by Date

**Steps:**
1. Go to Telemetry list
2. Use right sidebar filters:
   - **By timestamp**: Today, Past 7 days, This month
   - **By created at**: Today, Past 7 days, This month
3. Results update automatically

#### 3. Export Telemetry to CSV

**Steps:**
1. Go to Telemetry list
2. Select telemetry records (checkboxes)
3. Select action **"Export selected to CSV"** (if available)
4. Click **"Go"**
5. CSV file downloads automatically

---

### Creating and Managing Rules

#### 1. Create a New Rule

**Steps:**
1. Log in as `admin_user` or `operator_user`
2. Click **"Rules"** in sidebar
3. Click **"Add Rule"** button
4. Fill in the form:
   - **Name**: Rule name (e.g., `High Temperature Alert`)
   - **Description**: What the rule does
   - **Device Metric**: Select device and metric
   - **Condition**: JSON format condition
   - **Action**: JSON format action
   - **Is Active**: Check to enable

**Condition Example:**
```json
{
  "type": "threshold",
  "metric": "temperature",
  "operator": ">",
  "value": 30,
  "duration_minutes": 10
}
```

### 2. View All Rules

**Steps:**
1. Click **"Rules"** in sidebar
2. List shows:
   - ID
   - Name
   - Device Metric
   - Is Active

**Filtering:**
- Filter by active status (right sidebar)

**Search:**
- Search by rule name or device name

#### 3. Enable/Disable a Rule

**Steps:**
1. Go to Rules list
2. Click on the rule
3. Check/Uncheck **"Is Active"**
4. Click **"Save"**

#### 4. Edit Rule Conditions

**Steps:**
1. Click on the rule
2. Modify the **Condition** JSON field
3. Ensure valid JSON syntax
4. Click **"Save"**

**Tip:** Use a JSON validator before saving to avoid errors.

---

### Inspecting Events

#### 1. View Rule Trigger Events

**Steps:**
1. Click **"Events"** in sidebar
2. List shows:
   - ID
   - Rule (which rule triggered)
   - Timestamp (when it triggered)
   - Created At

#### 2. Filter Events by Date

**Steps:**
1. Go to Events list
2. Use right sidebar filters:
   - By timestamp
   - By created at
3. Select date range

#### 3. Find Events for Specific Rule

**Steps:**
1. Go to Events list
2. Use search box
3. Type rule name
4. Press Enter

#### 4. View Event Details

**Steps:**
1. Click on an event from the list
2. See full details:
   - Associated rule
   - Trigger timestamp
   - Creation timestamp

---

### Managing Metrics

#### 1. View Available Metrics

**Steps:**
1. Click **"Metrics"** in sidebar
2. See list of metric types:
   - Metric Type (e.g., `temperature`, `humidity`)
   - Data Type (e.g., `numeric`, `boolean`)

#### 2. Create a New Metric Type

**Steps:**
1. Click **"Add Metric"** button
2. Fill in:
   - **Metric Type**: Unique name (e.g., `pressure`)
   - **Data Type**: Choose from `numeric`, `boolean`, `string`
3. Click **"Save"**

#### 3. Link Metric to Device

**Steps:**
1. Click **"Device Metrics"** in sidebar
2. Click **"Add Device Metric"**
3. Select:
   - **Device**: Choose device
   - **Metric**: Choose metric type
4. Click **"Save"**

Now this device can send telemetry for this metric.

---

## Admin Actions

Admin actions are bulk operations you can perform on selected records.

### Available Actions

1. **Delete selected items** (Admin only)
   - Permanently removes records
   - Requires confirmation

2. **Export to CSV** (All roles)
   - Downloads selected records as CSV
   - Useful for reports

3. **Activate/Deactivate devices** (Operator, Admin)
   - Bulk enable/disable devices

### How to Use Admin Actions

1. Go to any list view (Devices, Rules, etc.)
2. Select items using checkboxes
3. Choose action from dropdown
4. Click **"Go"**
5. Confirm if prompted

---

## Troubleshooting

### Cannot See Admin Models

**Problem:** After login, no models visible in sidebar

**Solution:**
- Check your user role and permissions
- Viewer role only has read access
- Log in with `admin_user` for full access

### Cannot Delete Records

**Problem:** Delete button missing or greyed out

**Solution:**
- Only Admin and Superuser can delete
- Operator and Viewer cannot delete
- Check your role: go to Users → your username

### Rule Not Triggering

**Problem:** Created rule but no events generated

**Solution:**
1. Check rule is active (**Is Active** checkbox)
2. Verify condition JSON is valid
3. Check telemetry data matches condition
4. Look for errors in Django logs:
   ```bash
   docker logs web
