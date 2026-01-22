# IoT Hub Admin - Manual Acceptance Test Scenarios

This document contains step-by-step acceptance test scenarios for QA and demo purposes.

## Test Environment Setup

**Prerequisites:**
- IoT Hub running via `docker-compose up`
- Admin panel accessible at `http://localhost:8000/admin/`
- Test users created (automatic on startup)

**Test Users:**
- Superuser: `admin_from_script` / `admin123`
- Admin: `admin_user` / `admin123`
- Operator: `operator_user` / `operator123`
- Viewer: `viewer_user` / `viewer123`

---

## Scenario 1: Complete Device Lifecycle Management

**Objective:** Test the full lifecycle of a device from creation to deactivation, including telemetry and rules.

**Test Role:** Admin (`admin_user` / `admin123`)

**Estimated Time:** 10-15 minutes

### Step 1: Login to Admin Panel

1. Open browser and navigate to `http://localhost:8000/admin/`
2. Enter username: `admin_user`
3. Enter password: `admin123`
4. Click **"Log in"** button

**Expected Result:**
- ✅ Successfully logged in
- ✅ Admin dashboard visible with models: Devices, Telemetry, Metrics, Device Metrics, Rules, Events, Users

---

### Step 2: Create a New Device

1. Click **"Devices"** in the left sidebar
2. Click **"Add Device +"** button (top right)
3. Fill in the form:
   - **Serial ID:** `SN-TEST-001`
   - **Name:** `Test Humidity Sensor`
   - **Description:** `Humidity sensor for acceptance testing`
   - **User:** Select `testuser` from dropdown
   - **Is Active:** ✅ Checked
4. Click **"Save"** button

**Expected Result:**
- ✅ Success message: "The device "Test Humidity Sensor" was added successfully."
- ✅ Redirected to device list
- ✅ New device visible in the list with:
  - Serial ID: `SN-TEST-001`
  - Name: `Test Humidity Sensor`
  - User: `testuser`
  - Is Active: ✅ (green checkmark icon)

---

### Step 3: Link Metric to Device

1. Click **"Device Metrics"** in sidebar
2. Click **"Add Device Metric +"**
3. Fill in the form:
   - **Device:** Select `Test Humidity Sensor (SN-TEST-001)` from dropdown
   - **Metric:** Select `humidity` from dropdown (should exist from seed data)
4. Click **"Save"**

**Expected Result:**
- ✅ Success message: "The device metric ... was added successfully."
- ✅ Device-metric association created

**Note:** If `humidity` metric doesn't exist:
1. Go to **Metrics** → **Add Metric**
2. Create: Metric Type = `humidity`, Data Type = `numeric`
3. Return to Step 3

---

### Step 4: Create a Rule for the Device

1. Click **"Rules"** in sidebar
2. Click **"Add Rule +"**
3. Fill in the form:
   - **Name:** `Low Humidity Alert Test`
   - **Description:** `Alert when humidity drops below 35%`
   - **Device Metric:** Select the device-metric created in Step 3
   - **Condition:** Enter this JSON:
     ```json
     {
       "type": "threshold",
       "metric": "humidity",
       "operator": "<",
       "value": 35,
       "duration_minutes": 5
     }
     ```
   - **Action:** Enter this JSON:
     ```json
     {
       "type": "log",
       "level": "warning",
       "message": "Low humidity detected: {value}%"
     }
     ```
   - **Is Active:** ✅ Checked
4. Click **"Save"**

**Expected Result:**
- ✅ Success message: "The rule "Low Humidity Alert Test" was added successfully."
- ✅ Rule visible in rules list
- ✅ Is Active shows green checkmark

---

### Step 5: View and Verify Device Configuration

1. Click **"Devices"** in sidebar
2. Click on **"Test Humidity Sensor"** in the list
3. Verify all details are correct
4. Click **"History"** button (top right)

**Expected Result:**
- ✅ History shows creation event
- ✅ User who created it: `admin_user`
- ✅ Timestamp displayed

---

### Step 6: Search for the Device

1. Go to **"Devices"** list
2. In the search box (top right), type: `TEST-001`
3. Press Enter

**Expected Result:**
- ✅ Search filters list to show only `SN-TEST-001`
- ✅ One result displayed

---

### Step 7: Filter Active Devices

1. Go to **"Devices"** list
2. Look at right sidebar under **"Filter"**
3. Under **"By is active"**, click **"Yes"**

**Expected Result:**
- ✅ List shows only active devices
- ✅ `Test Humidity Sensor` is visible
- ✅ Filter indicator shows "is active: Yes"

---

### Step 8: Deactivate the Device

1. From filtered list, click on **"Test Humidity Sensor"**
2. Uncheck **"Is Active"** checkbox
3. Click **"Save"**

**Expected Result:**
- ✅ Success message: "The device "Test Humidity Sensor" was changed successfully."
- ✅ Device list shows red ✗ icon for Is Active

---

### Step 9: Verify Rule is Linked to Device

1. Click **"Rules"** in sidebar
2. Click on **"Low Humidity Alert Test"**
3. Verify **Device Metric** field shows correct device

**Expected Result:**
- ✅ Rule shows correct device-metric association
- ✅ Rule is still active

---

### Step 10: Delete the Test Device (Cleanup)

1. Go to **"Devices"** list
2. Check the checkbox next to **"Test Humidity Sensor"**
3. In the **"Action"** dropdown, select **"Delete selected devices"**
4. Click **"Go"** button
5. On confirmation page, review objects to be deleted
6. Click **"Yes, I'm sure"**

**Expected Result:**
- ✅ Success message: "Successfully deleted 1 device."
- ✅ Device removed from list
- ✅ Associated device-metric and rule also deleted (cascade)

---

### Test Scenario 1: Summary

**✅ PASS Criteria:**
- All 10 steps completed without errors
- Device created, configured, searched, filtered, deactivated, and deleted
- Rule successfully linked to device
- All UI elements responsive and functional

**❌ FAIL Criteria:**
- Any step produces an error
- Data not saved correctly
- Search/filter not working
- Cascade delete not working

---

## Scenario 2: Role-Based Access Control Testing

**Objective:** Verify that different user roles have correct permissions and restrictions.

**Test Roles:** Viewer, Operator, Admin

**Estimated Time:** 15-20 minutes

### Part A: Viewer Role Testing

#### Step 1: Login as Viewer

1. Logout from admin panel (top right → Log out)
2. Login with:
   - Username: `viewer_user`
   - Password: `viewer123`

**Expected Result:**
- ✅ Successfully logged in
- ✅ Dashboard visible

---

#### Step 2: Verify Read Access to Devices

1. Click **"Devices"** in sidebar
2. Observe the device list

**Expected Result:**
- ✅ Can see list of devices
- ✅ Can click on a device to view details

---

#### Step 3: Verify Cannot Add Devices

1. On Devices list page
2. Look for **"Add Device +"** button (top right)

**Expected Result:**
- ❌ **"Add Device +"** button NOT visible
- ✅ Only viewing is allowed

---

#### Step 4: Verify Cannot Edit Devices

1. Click on any device from the list
2. Observe the device detail page

**Expected Result:**
- ✅ All fields are read-only OR
- ❌ Save button should not work OR
- ✅ Edit page shows "You don't have permission to edit"

---

#### Step 5: Verify Cannot Delete Devices

1. Go back to Devices list
2. Check checkbox next to any device
3. Look at **"Action"** dropdown

**Expected Result:**
- ❌ Delete action NOT available in dropdown OR
- ✅ If selected, shows permission error

---

#### Step 6: Verify Can View Telemetry (Read-Only)

1. Click **"Telemetry"** in sidebar
2. View telemetry list
3. Try to click **"Add Telemetry +"** button

**Expected Result:**
- ✅ Can view telemetry list
- ❌ **"Add Telemetry +"** button NOT visible

---

### Part B: Operator Role Testing

#### Step 7: Login as Operator

1. Logout from viewer account
2. Login with:
   - Username: `operator_user`
   - Password: `operator123`

**Expected Result:**
- ✅ Successfully logged in

---

#### Step 8: Verify Can Add Devices

1. Click **"Devices"** in sidebar
2. Click **"Add Device +"** button
3. Fill in form:
   - Serial ID: `SN-OPERATOR-TEST`
   - Name: `Operator Test Device`
   - User: Select any user
   - Is Active: ✅
4. Click **"Save"**

**Expected Result:**
- ✅ Device created successfully
- ✅ Operator can add new devices

---

#### Step 9: Verify Can Edit Devices

1. Click on **"Operator Test Device"**
2. Change **Name** to `Operator Test Device - Modified`
3. Click **"Save"**

**Expected Result:**
- ✅ Device updated successfully
- ✅ Operator can edit devices

---

#### Step 10: Verify CANNOT Delete Devices

1. Go to Devices list
2. Check checkbox next to **"Operator Test Device - Modified"**
3. Look at **"Action"** dropdown

**Expected Result:**
- ❌ Delete action NOT available OR
- ✅ Attempting delete shows permission error

**Note:** Only Admin role should be able to delete.

---

#### Step 11: Verify Can Create Rules

1. Click **"Rules"** in sidebar
2. Click **"Add Rule +"**
3. Create a simple rule (any valid data)
4. Click **"Save"**

**Expected Result:**
- ✅ Rule created successfully
- ✅ Operator can create and modify rules

---

### Part C: Admin Role Testing

#### Step 12: Login as Admin

1. Logout from operator account
2. Login with:
   - Username: `admin_user`
   - Password: `admin123`

**Expected Result:**
- ✅ Successfully logged in

---

#### Step 13: Verify Can Delete Devices

1. Click **"Devices"** in sidebar
2. Find **"Operator Test Device - Modified"**
3. Check its checkbox
4. Select **"Delete selected devices"** from Action dropdown
5. Click **"Go"**
6. Confirm deletion

**Expected Result:**
- ✅ Device deleted successfully
- ✅ Admin has full delete permissions

---

#### Step 14: Verify Can Delete Telemetry

1. Click **"Telemetry"** in sidebar
2. Select any telemetry record
3. Select **"Delete selected telemetry"** action
4. Click **"Go"** and confirm

**Expected Result:**
- ✅ Telemetry deleted successfully
- ✅ Admin can delete any data

---

### Test Scenario 2: Summary

**✅ PASS Criteria:**
- Viewer: Can ONLY view, cannot add/edit/delete
- Operator: Can view/add/edit, CANNOT delete
- Admin: Can view/add/edit/delete (full access)

**❌ FAIL Criteria:**
- Viewer can modify data
- Operator can delete data
- Admin cannot delete data
- Any permission leakage

---

## Scenario 3: Telemetry Data Flow and Event Inspection

**Objective:** Verify telemetry data can be viewed, filtered, and linked to devices. Inspect rule events.

**Test Role:** Admin (`admin_user` / `admin123`)

**Estimated Time:** 10 minutes

### Step 1: Login as Admin

1. Navigate to `http://localhost:8000/admin/`
2. Login with: `admin_user` / `admin123`

**Expected Result:**
- ✅ Successfully logged in

---

### Step 2: View All Telemetry Data

1. Click **"Telemetry"** in sidebar
2. Observe the list

**Expected Result:**
- ✅ List displays telemetry records with columns:
  - ID
  - Device Metric
  - Value (JSON format)
  - Timestamp (ts)
  - Created At
- ✅ Multiple records visible (from seed data)

---

### Step 3: Search Telemetry by Device Name

1. In the search box (top right), type: `Test Device 1`
2. Press Enter

**Expected Result:**
- ✅ List filters to show only telemetry from "Test Device 1"
- ✅ Search works across device names

---

### Step 4: Filter Telemetry by Date

1. Clear search box
2. Look at right sidebar under **"By ts"** (timestamp)
3. Click **"Today"**

**Expected Result:**
- ✅ List shows only today's telemetry
- ✅ Date filter works

---

### Step 5: View Telemetry Details

1. Click on any telemetry record
2. Observe the detail page

**Expected Result:**
- ✅ Shows full details:
  - Device Metric (device + metric type)
  - Value JSONB (e.g., `{"t": "numeric", "v": "25.5"}`)
  - Timestamp
  - Created At

---

### Step 6: Verify Telemetry Linked to Correct Device

1. From telemetry detail page, note the **Device Metric**
2. Click **"Devices"** in sidebar
3. Find the corresponding device
4. Click on the device

**Expected Result:**
- ✅ Device name matches the device in telemetry
- ✅ Correct linkage verified

---

### Step 7: View All Events

1. Click **"Events"** in sidebar
2. Observe the events list

**Expected Result:**
- ✅ List displays events with columns:
  - ID
  - Rule (name)
  - Timestamp (when rule triggered)
  - Created At
- ✅ Multiple events visible (from seed data)

---

### Step 8: Search Events by Rule Name

1. In search box, type the rule name (e.g., `High Temperature`)
2. Press Enter

**Expected Result:**
- ✅ List filters to show only events for that rule
- ✅ Search works

---

### Step 9: Filter Events by Timestamp

1. Clear search
2. In right sidebar under **"By timestamp"**, click **"Past 7 days"**

**Expected Result:**
- ✅ Shows events from last 7 days
- ✅ Date filter works

---

### Step 10: View Event Details and Trace Back to Rule

1. Click on any event from the list
2. Note the **Rule** name
3. Click **"Rules"** in sidebar
4. Find and click on the rule from Step 2
5. Verify rule configuration

**Expected Result:**
- ✅ Event correctly linked to rule
- ✅ Rule shows correct condition and action
- ✅ Full audit trail visible

---

### Step 11: Count Telemetry Records

1. Go to **"Telemetry"** list
2. Look at bottom of page for pagination info (e.g., "10 results")
3. Note the total count

**Expected Result:**
- ✅ Pagination shows correct count
- ✅ At least 10 telemetry records exist (from seed data)

---

### Step 12: Count Events

1. Go to **"Events"** list
2. Look at pagination info
3. Note the total count

**Expected Result:**
- ✅ At least 5 events exist (from seed data)
- ✅ Count displayed correctly

---

### Test Scenario 3: Summary

**✅ PASS Criteria:**
- Telemetry data visible and searchable
- Filtering by date works
- Telemetry correctly linked to devices
- Events visible and linked to rules
- Full data traceability from event → rule → device → telemetry

**❌ FAIL Criteria:**
- Telemetry not displayed
- Search/filter not working
- Broken links between models
- Incorrect data shown

---

## Test Execution Checklist

Use this checklist when running acceptance tests:

- [ ] **Scenario 1** - Device Lifecycle (10-15 min)
  - [ ] Steps 1-10 completed
  - [ ] All PASS criteria met
  - [ ] No errors encountered

- [ ] **Scenario 2** - Role-Based Access (15-20 min)
  - [ ] Part A: Viewer testing completed
  - [ ] Part B: Operator testing completed
  - [ ] Part C: Admin testing completed
  - [ ] All PASS criteria met

- [ ] **Scenario 3** - Telemetry & Events (10 min)
  - [ ] Steps 1-12 completed
  - [ ] All PASS criteria met
  - [ ] Data traceability verified

---

## Reporting Issues

If any test fails, report with:

1. **Scenario & Step Number:** (e.g., "Scenario 1, Step 4")
2. **Expected Result:** What should happen
3. **Actual Result:** What actually happened
4. **Screenshot:** If possible
5. **Browser & Version:** (e.g., Chrome 120)
6. **Docker Logs:** Run `docker logs web` and attach relevant errors

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-22
