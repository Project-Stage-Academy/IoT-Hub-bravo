#!/bin/sh
set -e

# =============================
# Configuration
# =============================
ENABLE_TIMESCALEDB=${ENABLE_TIMESCALEDB:-true}

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

#exec gunicorn conf.wsgi:application --bind 0.0.0.0:8000 --workers=2 --threads=4

exec daphne -b 0.0.0.0 -p 8000 conf.asgi:application