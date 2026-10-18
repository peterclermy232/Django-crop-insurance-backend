#!/usr/bin/env bash
# Render build script: install deps, collect static files, migrate and seed.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_data
python manage.py seed_roles
python manage.py import_kenya_locations

# Create the first admin account once, if credentials were provided.
if [[ -n "${DJANGO_SUPERUSER_USER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --noinput || echo "Superuser already exists, skipping."
fi
