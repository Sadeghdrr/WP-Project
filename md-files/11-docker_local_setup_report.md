# Docker Local Setup Report

**Branch:** `feat/docker-local-setup`  
**Date:** February 22, 2026

---

## Problem

The project had an empty `docker-compose.yaml` and no Dockerfiles. Running the stack locally required manually installing Python/Node dependencies, managing a local PostgreSQL instance, and remembering to run migrations and `collectstatic` by hand. There was no reproducible, one-command local dev environment.

---

## Solution

A clean, three-service Docker Compose stack was created — **no nginx required**. WhiteNoise (already configured in `settings.py`) serves static files directly from Gunicorn. Vite's dev server provides hot-module-replacement for the frontend.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  docker compose up --build                                  │
│                                                             │
│  ┌──────────┐    healthy    ┌──────────┐   ┌────────────┐  │
│  │    db    │ ◄──depends──  │ backend  │   │  frontend  │  │
│  │ postgres │               │ gunicorn │   │   vite     │  │
│  │  :5432   │               │  :8000   │   │   :5173    │  │
│  └──────────┘               └──────────┘   └────────────┘  │
│                                                             │
│  All services read WP-Project/.env via env_file             │
└─────────────────────────────────────────────────────────────┘
```

---

## Files Created / Modified

| File | Action |
|---|---|
| `WP-Project/docker-compose.yaml` | **Updated** — full three-service compose definition |
| `WP-Project/backend/Dockerfile` | **Created** — `python:3.12-slim`, installs deps, copies entrypoint |
| `WP-Project/backend/entrypoint.sh` | **Created** — waits for DB, runs migrate + collectstatic, starts Gunicorn |
| `WP-Project/frontend/Dockerfile` | **Created** — `node:20-alpine`, runs `npm ci` |
| `WP-Project/backend/.dockerignore` | **Created** — excludes cache, venvs, secrets, artefacts |
| `WP-Project/frontend/.dockerignore` | **Created** — excludes node_modules, dist, secrets |
| `WP-Project/backend/requirements.txt` | **Modified** — added `gunicorn>=22.0.0` |
| `WP-Project/.env.example` | **Modified** — clarified `DB_HOST=db` for Docker vs `localhost` for bare-metal |

---

## Service Details

### `db` — PostgreSQL 16

- Image: `postgres:16-alpine`
- Named volume `postgres_data` persists data across container restarts.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` are mapped from `.env`'s `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- Healthcheck: `pg_isready -U $DB_USER -d $DB_NAME` (5s interval, 10 retries).

### `backend` — Django + Gunicorn

- Built from `backend/Dockerfile` (`python:3.12-slim`).
- `./:/app` volume-mounted so code changes are reflected immediately (no rebuild needed).
- `working_dir: /app/backend` — Gunicorn is launched from here so `backend.wsgi` resolves correctly.
- `settings.py` uses `Path(__file__).resolve().parents[2]` → `/app` → reads `/app/.env`. ✓
- `entrypoint.sh` automations:
  1. `nc -z $DB_HOST $DB_PORT` loop — waits until Postgres accepts connections.
  2. `python manage.py migrate --noinput`
  3. `python manage.py collectstatic --noinput`
  4. `python manage.py setup_rbac` — seeds all Roles and links permissions (idempotent).
  5. Creates the default superuser via `manage.py shell` heredoc (idempotent — skips if username already exists). Credentials are read from `DJANGO_SUPERUSER_*` env vars; defaults: `admin` / `1234`.
  6. `exec gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120`

### `frontend` — Vite Dev Server

- Built from `frontend/Dockerfile` (`node:20-alpine`).
- `npm ci` installed at build time (cached layer).
- `./:/app` mount for HMR; anonymous volume `/app/frontend/node_modules` prevents the host mount from shadowing container-installed packages.
- `envDir` in `vite.config.ts` points to `/app` → reads `/app/.env` at runtime. ✓
- Launched with `--host 0.0.0.0` so the port is reachable from the host.

---

## How to Run Locally (Docker)

```bash
# 1. Copy and fill in the template
cp .env.example .env
# Edit .env:
#   SECRET_KEY=<generate one>
#   DB_HOST=db               <- must be "db" for Docker networking
#   DB_NAME=wpproject
#   DB_USER=wpuser
#   DB_PASSWORD=yourpassword
#   VITE_API_BASE_URL=http://localhost:8000/api

# 2. Build and start all services
docker compose --env-file ./.env up --build

# Services will be available at:
#   Django API  → http://localhost:8000
#   Vite app    → http://localhost:5173
#   Admin panel → http://localhost:8000/admin

# 3. Stop and remove containers (data persists in postgres_data volume)
docker compose down

# 4. Full reset (removes DB data too)
docker compose down -v
```

### Useful one-liners

```bash
# Run a Django management command inside the backend container
docker compose exec backend python manage.py createsuperuser

# Tail backend logs
docker compose logs -f backend

# Force rebuild after requirements.txt change
docker compose up --build backend
```

---

## Pitfalls & Notes

### `DB_HOST` must be `db` in Docker

Inside Docker Compose, service-to-service communication uses the **service name** as the hostname. `DB_HOST=localhost` works for bare-metal dev but breaks inside Docker. Set `DB_HOST=db` in `.env` when using Compose.

### CORS / CSRF with `localhost:5173`

`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` in `.env` must include `http://localhost:5173`. The defaults in `settings.py` already cover this, but if you change ports, update both variables.

### `collectstatic` manifest

`CompressedManifestStaticFilesStorage` writes a `staticfiles.json` manifest during `collectstatic`. If `STATIC_ROOT` is inside the mounted volume (`/app/backend/staticfiles/`) the file persists across restarts — no re-collection needed unless static sources change. If the manifest is missing, Django raises `ValueError: Missing staticfiles manifest entry`.

### `VITE_` prefix requirement

Vite strips any `.env` variable **not** prefixed with `VITE_` from `import.meta.env`. Backend-only secrets (`SECRET_KEY`, `DB_PASSWORD`, etc.) are safe even though they share the same `.env` file.

### `node_modules` anonymous volume

The compose file uses an anonymous volume for `/app/frontend/node_modules`. This prevents the `./:/app` bind mount from hiding the container's installed packages if `node_modules/` does not exist on the host. If you run `npm install` locally, the host directory takes precedence — running `docker compose down -v` clears the anonymous volume and forces a fresh `npm ci` on next start.

### `gunicorn` added to `requirements.txt`

`gunicorn>=22.0.0` was added because it was not present and is required for the production WSGI server.

### Default superuser credentials

The superuser is created automatically on first container start with these defaults:

| Variable | Default |
|---|---|
| `DJANGO_SUPERUSER_USERNAME` | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | `1234` |
| `DJANGO_SUPERUSER_EMAIL` | `admin@admin.com` |
| `DJANGO_SUPERUSER_NATIONAL_ID` | `0000000000` |
| `DJANGO_SUPERUSER_PHONE` | `09000000000` |

Override any of these in `.env` before the first `docker compose up`. The creation is **idempotent** — if the username already exists the step is silently skipped.

> **Security:** Change `DJANGO_SUPERUSER_PASSWORD` and `DJANGO_SUPERUSER_NATIONAL_ID` before any deployment outside your local machine.

### RBAC seeding (`setup_rbac`)

`python manage.py setup_rbac` runs after every `migrate`. It is idempotent — it creates/updates Roles and their Permission links but never deletes existing data. If permissions don't exist yet (e.g., a fresh migration run), re-running `setup_rbac` after `migrate` will pick them up correctly.
