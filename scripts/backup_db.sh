#!/bin/bash
set -euo pipefail

# --- Configuration ---
BACKUP_DIR="./backups"
DB_NAME="iot_hub_db"
DB_USER="iot_user_db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/snapshot_$TIMESTAMP.dump"

# Create directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting database backup for $DB_NAME..."

# Execute dump
docker compose exec -T db pg_dump \
  -U "$DB_USER" -d "$DB_NAME" \
  --format=custom \
  --no-owner --no-privileges \
  > "$BACKUP_FILE"

echo "Backup created successfully: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"

# --- Cleanup ---
# Remove backups older than 7 days to save disk space
find "$BACKUP_DIR" -name "snapshot_*.dump" -mtime +7 -delete
echo "Old backups (older than 7 days) have been removed."