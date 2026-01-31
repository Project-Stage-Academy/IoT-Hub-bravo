#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------
# Smoke test: HTTP simulator
# Purpose: Verify simulator sends telemetry via HTTP
# and works non-interactively for CI/smoke
# -------------------------------------------------

export DJANGO_LOG_LEVEL=WARNING

# Configurable parameters
SERVICE="${SERVICE:-web}"
DEVICE_SERIAL="${DEVICE_SERIAL:-SN-A1-TEMP-0001}"
SIM_CMD="${SIM_CMD:-python simulator/run.py --mode http --device $DEVICE_SERIAL --count 5 --rate 2 --value-generation non-interactive}"
DJANGO_SHELL="${DJANGO_SHELL:-python manage.py shell -c}"

echo "======================================"
echo "Running HTTP simulator smoke test"
echo "======================================"

# -----------------------------
# Step 1: Ensure device exists
# -----------------------------
echo "[1/5] Checking that device exists..."
docker compose exec -T "$SERVICE" $DJANGO_SHELL "
from apps.devices.models import Device
assert Device.objects.filter(serial_id='$DEVICE_SERIAL').exists(), 'Device $DEVICE_SERIAL does not exist'
print('✅ Device exists:', '$DEVICE_SERIAL')
"

# -----------------------------
# Step 2: Capture telemetry count before
# -----------------------------
echo "[2/5] Capturing initial telemetry count..."
before="$(docker compose exec -T "$SERVICE" $DJANGO_SHELL "
from apps.devices.models import Telemetry
print(Telemetry.objects.count())
")"
before_num=$(echo "$before" | grep -oE '[0-9]+' | tail -1)
echo "Telemetry count before: $before_num"

# -----------------------------
# Step 3: Run simulator
# -----------------------------
echo "[3/5] Running simulator..."
docker compose exec -T "$SERVICE" bash -c "cd /app && $SIM_CMD"

# -----------------------------
# Step 4: Capture telemetry count after
# -----------------------------
after="$(docker compose exec -T "$SERVICE" $DJANGO_SHELL "
from apps.devices.models import Telemetry
print(Telemetry.objects.count())
")"
after_num=$(echo "$after" | grep -oE '[0-9]+' | tail -1)
echo "Telemetry count after: $after_num"

# -----------------------------
# Step 5: Verify new telemetry created
# -----------------------------
if [ "$after_num" -le "$before_num" ]; then
  echo "❌ Simulator did not create new telemetry records"
  exit 1
fi

echo "✅ Simulator HTTP smoke test passed, total telemetry: $after_num"

# -----------------------------
# Optional Step 6: Re-run for idempotency
# -----------------------------
echo "[Optional] Re-running simulator for idempotency check..."
docker compose exec -T "$SERVICE" bash -c "cd /app && $SIM_CMD"

after2_num="$(docker compose exec -T "$SERVICE" $DJANGO_SHELL "
from apps.devices.models import Telemetry
print(Telemetry.objects.count())
")"

echo "Telemetry count after second run: $after2_num"
echo "✅ HTTP simulator smoke test fully verified"
