#!/usr/bin/env sh
set -eu

echo "[backend] Waiting for PostgreSQL..."
until python -c "import psycopg; psycopg.connect('dbname=' + '${POSTGRES_DB}' + ' user=' + '${POSTGRES_USER}' + ' password=' + '${POSTGRES_PASSWORD}' + ' host=' + '${POSTGRES_HOST}' + ' port=' + '${POSTGRES_PORT}').close()"; do
  sleep 2
done

echo "[backend] Running migrations..."
python -m alembic upgrade head

echo "[backend] Seeding default data..."
python -m app.db.init_db

echo "[backend] Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
