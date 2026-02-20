#!/bin/sh
set -e

# =============================
# Configuration
# =============================
ENABLE_TIMESCALEDB=${ENABLE_TIMESCALEDB:-true}
ENABLE_SEED_DATA=${ENABLE_SEED_DATA:-true}

# =============================
# Helpers
# =============================
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# =============================
# Django migrations
# =============================
log "Running migrations..."
python manage.py migrate --noinput || {
  log "Migration failed."
  exit 1
}
log "Migrations completed."

# =============================
# TimescaleDB setup (optional)
# =============================
if [ "$ENABLE_TIMESCALEDB" = "true" ]; then
  log "Setting up TimescaleDB..."
  python manage.py setup_timescaledb || {
    log "TimescaleDB setup failed."
    exit 1
  }
  log "TimescaleDB setup completed."
else
  log "Skipping TimescaleDB setup (ENABLE_TIMESCALEDB=false)."
fi

# =============================
# Database seeding (optional)
# =============================
if [ "$ENABLE_SEED_DATA" = "true" ]; then
  log "Seeding database..."
  python manage.py seed_dev_data || {
    log "Seeding failed."
    exit 1
  }
  log "Seeding completed."
else
  log "Skipping database seeding (ENABLE_SEED_DATA=false)."
fi

# =============================
# Setup admin users & groups
# =============================
if [ "${ALLOW_SETUP_ADMIN:-false}" = "true" ]; then
  log "Setting up admin users and permissions..."
  python manage.py setup_admin || {
    log "Admin setup failed (non-critical, continuing)."
  }
  log "Admin setup completed."
fi

exec daphne -b 0.0.0.0 -p 8000 conf.asgi:application