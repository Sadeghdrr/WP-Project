#!/bin/sh
# =============================================================================
# WP-Project/backend/entrypoint.sh
#
# Container startup script for the Django backend service.
# Executed as the ENTRYPOINT of the backend container.
#
# Steps:
#   1. Wait until PostgreSQL is accepting connections
#   2. Run database migrations
#   3. Collect static files (WhiteNoise serves them)
#   4. Start Gunicorn
#
# Environment variables DB_HOST and DB_PORT are injected via env_file in
# docker-compose, so no defaults need to be hard-coded here.
# =============================================================================

set -e

# ── 1. Wait for Postgres ──────────────────────────────────────────────────────
echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} ..."
until nc -z "${DB_HOST}" "${DB_PORT}"; do
    echo "[entrypoint]   ... not ready yet, sleeping 2s"
    sleep 2
done
echo "[entrypoint] PostgreSQL is up."

# ── 2. Migrations ─────────────────────────────────────────────────────────────
echo "[entrypoint] Running migrations ..."
python manage.py migrate --noinput

# ── 3. Collect static files ───────────────────────────────────────────────────
echo "[entrypoint] Collecting static files ..."
python manage.py collectstatic --noinput

# ── 4. Start Gunicorn ─────────────────────────────────────────────────────────
# WSGI module path: backend.wsgi  (Django project package name = backend)
# working_dir is /app/backend (set in compose), so this resolves correctly.
echo "[entrypoint] Starting Gunicorn ..."
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --log-level "${LOG_LEVEL:-info}"
