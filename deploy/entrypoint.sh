#!/bin/sh
set -eu

# Refuse to start with the insecure development fallback key
: "${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY must be set in .env}"

# Create or update tables (idempotent, safe on every start)
python manage.py migrate --noinput

# 2 processes x 4 threads is plenty for SQLite (more writers would just contend on the DB lock)
exec gunicorn config.wsgi:application \
  --chdir /app/django_backend \
  --bind 0.0.0.0:8000 \
  --workers 2 --threads 4 \
  --timeout 60 \
  --access-logfile -