#!/bin/sh
set -e

# -----------------------------
# Run Django migrations
# -----------------------------
echo "Running migrations..."
python manage.py migrate --noinput || { echo "Migration failed"; exit 1; }
echo "Migrations completed."

exec gunicorn conf.wsgi:application --bind 0.0.0.0:8000 --workers=2 --threads=4