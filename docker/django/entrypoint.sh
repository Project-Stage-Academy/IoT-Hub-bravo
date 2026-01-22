#!/bin/sh
set -e

# -----------------------------
# Wait for PostgreSQL with timeout
# -----------------------------
TIMEOUT=30 # seconds
COUNT=0

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$TIMEOUT" ]; then
    echo "Timeout ($TIMEOUT s). PostgreSQL is not ready."
    exit 1
  fi
  sleep 1
done

echo "PostgreSQL is ready!"

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

#-----------------------------
#Setup Admin Users & Groups
#-----------------------------
echo "Setting up admin users and permissions..."
python manage.py setup_admin || { echo "Admin setup failed"; exit 1; }
echo "Admin setup completed."

#-----------------------------
#Print Access Information
#-----------------------------
echo ""
echo "=========================================="
echo "🚀 IoT Hub Development Environment Ready!"
echo "=========================================="
echo ""
echo "🔑 Admin Users Available:"
echo " - Superuser: admin_from_script / admin123"
echo " - Admin: admin_user / admin123"
echo " - Operator: operator_user / operator123"
echo " - Viewer: viewer_user / viewer123"
echo ""
echo "🌐 Admin Panel: http://localhost:8000/admin/"
echo "=========================================="
echo ""

exec "$@"
