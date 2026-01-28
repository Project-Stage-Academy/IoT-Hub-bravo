#!/bin/sh
set -e

# =============================
# Helpers
# =============================
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# =============================
# Configuration
# =============================
TIMEOUT=30 # seconds
COUNT=0
ENABLE_TIMESCALEDB=${ENABLE_TIMESCALEDB:-true}
ENABLE_SEED_DATA=${ENABLE_SEED_DATA:-true}

# =============================
# Wait for PostgreSQL
# =============================
log "Waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$TIMEOUT" ]; then
    log "Timeout (${TIMEOUT}s). PostgreSQL is not ready."
    exit 1
  fi
  sleep 1
done

log "PostgreSQL is ready."

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
  python manage.py seed_db || {
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
log "Setting up admin users and permissions..."
python manage.py setup_admin || {
  log "Admin setup failed."
  exit 1
}
log "Admin setup completed."

# =============================
# Print access information
# =============================
log "Admin users available:"
log " - Superuser: ${DEV_SUPERUSER_USERNAME:-admin_from_script}"
log " - Admin: ${DEV_ADMIN_USERNAME:-admin_user}"
log " - Operator: ${DEV_OPERATOR_USERNAME:-operator_user}"
log " - Viewer: ${DEV_VIEWER_USERNAME:-viewer_user}"
log "Admin panel available at: http://localhost:8000/admin/"

# =============================
# Start main process
# =============================
exec "$@"
