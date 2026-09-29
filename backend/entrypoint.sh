#!/bin/sh
set -e

echo "Waiting for database to be ready..."

: "${DB_HOST:?Need to set DB_HOST}"
: "${DB_PORT:?Need to set DB_PORT}"

timeout=60
counter=0

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
  counter=$((counter + 1))
  if [ "$counter" -ge "$timeout" ]; then
    echo "Database connection timeout after ${timeout}s"
    exit 1
  fi
  echo "Waiting for database... (${counter}/${timeout}s)"
done

echo "Database is ready"

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  alembic -c backend/alembic.ini upgrade head
  echo "Migrations completed"
else
  echo "Skipping migrations (RUN_MIGRATIONS!=true)"
fi

echo "Starting application..."
exec "$@"
