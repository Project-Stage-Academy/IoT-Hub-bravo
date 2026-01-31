#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------
# Smoke test for seed_dev_data
# Purpose: Verify that demo data is seeded correctly
# and that the command is idempotent
# -------------------------------------------------

export DJANGO_LOG_LEVEL=WARNING

# Configurable service & commands
SERVICE="${SERVICE:-web}"
SEED_CMD="${SEED_CMD:-python manage.py seed_dev_data}"
DJANGO_SHELL="${DJANGO_SHELL:-python manage.py shell -c}"

echo "======================================"
echo "Running seed_dev_data smoke test"
echo "======================================"

# -----------------------------
# Step 1: Initial seeding
# -----------------------------
echo "[1/4] Seeding initial data..."
docker compose exec -T "$SERVICE" $SEED_CMD

# -----------------------------
# Step 2: Validate core objects
# -----------------------------
echo "[2/4] Validating created objects..."
docker compose exec -T "$SERVICE" $DJANGO_SHELL "
from apps.devices.models import Device
from apps.rules.models import Rule

# Assertions
assert Device.objects.exists(), 'No devices created!'
assert Rule.objects.exists(), 'No rules created!'

print('✅ Core objects exist:',
      'Devices:', Device.objects.count(),
      'Rules:', Rule.objects.count())
"

# -----------------------------
# Step 3: Capture counts before re-seed
# -----------------------------
echo "[3/4] Capturing counts for idempotency check..."
counts_before="$(docker compose exec -T "$SERVICE" $DJANGO_SHELL "
from apps.devices.models import Device
from apps.rules.models import Rule
print(Device.objects.count(), Rule.objects.count())
")"

# -----------------------------
# Step 4: Re-run seed_dev_data
# -----------------------------
echo "[4/4] Re-running seed_dev_data to test idempotency..."
docker compose exec -T "$SERVICE" $SEED_CMD

# -----------------------------
# Step 5: Capture counts after re-seed
# -----------------------------
counts_after="$(docker compose exec -T "$SERVICE" $DJANGO_SHELL "
from apps.devices.models import Device
from apps.rules.models import Rule
print(Device.objects.count(), Rule.objects.count())
")"

# -----------------------------
# Step 6: Compare counts to ensure idempotency
# -----------------------------
if [ "$counts_before" != "$counts_after" ]; then
  echo "❌ Seed command is not idempotent!"
  echo "Before: $counts_before"
  echo "After : $counts_after"
  exit 1
fi

echo "✅ seed_dev_data is idempotent and functional. Counts: $counts_after"
