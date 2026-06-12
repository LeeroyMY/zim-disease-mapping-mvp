#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Starting Gunicorn..."
# Bind to 0.0.0.0:8000 as expected by Render Docker environments
# or Render assigns PORT environment variable
PORT=${PORT:-8000}
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
