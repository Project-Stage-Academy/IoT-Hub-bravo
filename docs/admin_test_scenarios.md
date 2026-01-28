## Manual Acceptance Test Scenarios

### Scenario 1: Device Management Workflow

**Objective:** Verify device creation, modification, and bulk actions.

**Preconditions:**
- Logged in as `admin_user` or `superadmin`
- At least one user exists in the system

**Steps:**

1. Navigate to **Devices > Devices**
2. Click **Add Device**
3. Fill in:
   - Serial ID: `TEST-DEVICE-001`
   - Name: `Test Temperature Sensor`
   - Description: `Sensor for QA testing`
   - User: Select any user
   - Is active: ✓ Checked
4. Click **Save**
5. **Expected:** Device created, redirected to device list, success message shown
6. Click on `TEST-DEVICE-001` to edit
7. Change Name to `Updated Test Sensor`
8. Click **Save**
9. **Expected:** Changes saved, success message shown
10. Return to device list, select `TEST-DEVICE-001`
11. Select action **Disable selected devices**, click **Go**
12. **Expected:** Device `is_active` becomes False, success message shows "1 device(s) successfully disabled"
13. Select same device, choose **Enable selected devices**, click **Go**
14. **Expected:** Device `is_active` becomes True

**Result:** ☐ Pass / ☐ Fail

---

### Scenario 2: Telemetry Export Workflow

**Objective:** Verify telemetry viewing and CSV export functionality.

**Preconditions:**
- Logged in as `operator_user` or higher
- At least one device with telemetry data exists

**Steps:**

1. Navigate to **Devices > Devices**
2. Click on a device with telemetry data
3. Expand **Telemetry Data** section
4. **Expected:** "Latest Telemetry" shows timestamp, "Recent Telemetry (Last 10)" shows table with data
5. Navigate to **Devices > Telemetrys**
6. **Expected:** List shows telemetry records with ID, Device Metric, Value, Timestamp
7. Use date hierarchy to filter by today's date
8. **Expected:** List filters to show only today's records
9. Select 3-5 telemetry records (checkboxes)
10. Select action **Export selected telemetry to CSV**, click **Go**
11. **Expected:** CSV file downloads with filename `telemetry_export.csv`
12. Open CSV file
13. **Expected:** CSV contains columns: ID, Device, Metric, Value, Timestamp, Created At

**Result:** ☐ Pass / ☐ Fail

---

### Scenario 3: Rule and Event Management Workflow

**Objective:** Verify rule creation and event acknowledgment.

**Preconditions:**
- Logged in as `operator_user` or higher
- At least one DeviceMetric exists
- Some events exist in the system

**Steps:**

1. Navigate to **Rules > Rules**
2. Click **Add Rule**
3. Fill in:
   - Name: `Test High Value Alert`
   - Description: `Alert when value exceeds threshold`
   - Device metric: Select any available
   - Condition: `{"operator": ">", "value": 100}`
   - Action: `{"type": "alert", "severity": "warning"}`
   - Is active: ✓ Checked
4. Click **Save**
5. **Expected:** Rule created, success message shown
6. Verify rule appears in list with Status = True (green checkmark)
7. Navigate to **Rules > Events**
8. **Expected:** Event list shows with columns: ID, Rule, Device, Acknowledged, Timestamp
9. Select 2-3 unacknowledged events
10. Select action **Mark selected events as acknowledged**, click **Go**
11. **Expected:** Events now show Acknowledged = True, success message shows count
12. Select same events, choose **Mark selected events as unacknowledged**, click **Go**
13. **Expected:** Events return to Acknowledged = False

**Result:** ☐ Pass / ☐ Fail