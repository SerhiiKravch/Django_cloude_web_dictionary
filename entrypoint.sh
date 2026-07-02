#!/bin/sh
set -e

if [ "${DB_ENGINE}" = "django.db.backends.postgresql" ]; then
  echo "Waiting for PostgreSQL at ${DB_HOST:-db}:${DB_PORT:-5432}..."
  until nc -z "${DB_HOST:-db}" "${DB_PORT:-5432}"; do
    sleep 1
  done
  echo "PostgreSQL is available."
fi

python manage.py migrate --noinput

exec "$@"
