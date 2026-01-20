#!/bin/sh
set -e

# wait_for_db - add in the future
python manage.py migrate --noinput || exit 1

exec "$@"
