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
#   4. Seed roles and permissions (setup_rbac — idempotent)
#   5. Create default superuser if it does not exist (idempotent)
#      username: admin  |  password: 1234
#   6. Start Gunicorn
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

# ── 4. Seed RBAC roles & permissions ─────────────────────────────────────────
# The setup_rbac command is idempotent — safe to re-run on every start.
echo "[entrypoint] Setting up RBAC roles and permissions ..."
python manage.py setup_rbac

# ── 5. Create default superuser (idempotent) ──────────────────────────────────
echo "[entrypoint] Creating default superuser if needed ..."
python manage.py shell << 'PYEOF'
from accounts.models import User, Role

if not User.objects.filter(username="admin").exists():
    role = Role.objects.filter(name="System Admin").first()
    User.objects.create_superuser(
        username="admin",
        password="1234",
        email="admin@admin.com",
        national_id="0000000000",
        phone_number="09000000000",
        first_name="Admin",
        last_name="Admin",
        role=role,
    )
    print("[entrypoint] Superuser 'admin' created.")
else:
    print("[entrypoint] Superuser 'admin' already exists — skipping.")
PYEOF

# ── 6. Start Gunicorn ─────────────────────────────────────────────────────────
# WSGI module path: backend.wsgi  (Django project package name = backend)
# working_dir is /app/backend (set in compose), so this resolves correctly.
echo "[entrypoint] Starting Gunicorn ..."
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --log-level "${LOG_LEVEL:-info}"
