#!/bin/sh
set -e

# -----------------------------
# Run Django migrations
# -----------------------------
echo "Running migrations..."
python manage.py migrate --noinput || { echo "Migration failed"; exit 1; }
echo "Migrations completed."

# -----------------------------
# Seed Database
# -----------------------------
echo "Seeding database..."
python manage.py seed_db || { echo "Seeding failed"; exit 1; }
echo "Seeding completed."

exec python manage.py runserver 0.0.0.0:8000
