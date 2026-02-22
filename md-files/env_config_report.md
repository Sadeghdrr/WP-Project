# Environment Configuration Report

**Branch:** `feat/env-config-dotenv-whitenoise`  
**Date:** February 22, 2026

---

## Problem

The project had multiple shortcomings in its configuration layer:

1. `SECRET_KEY` was hard-coded directly in `settings.py` and committed to the repository.
2. `DEBUG = True` and `ALLOWED_HOSTS = ['*']` were hardcoded — unsafe for any deployment.
3. The database was SQLite with a hard-coded path; there was no PostgreSQL configuration.
4. No `.env` support existed: every developer had to manually export OS environment variables or edit `settings.py` locally.
5. WhiteNoise was not set up, so serving static files in production required a separate web server or CDN configuration that was never documented.
6. Vite (frontend) had no way to share the same `.env` file with Django, so API URLs were scattered or hard-coded in the frontend code.
7. CORS middleware was present in `INSTALLED_APPS` but `CorsMiddleware` was missing from `MIDDLEWARE`.

---

## Solution

### 1. Single root `.env` file

A single `WP-Project/.env` file is the one source of truth for all configuration.  
Django loads it via **python-dotenv**; Vite reads it via the new `envDir` setting.  
No OS-level `export` commands are required — the workflow is simply:

```
cp .env.example .env   # fill in real values
cd backend && python manage.py runserver
cd frontend && npm run dev
```

### 2. `env_get()` – typed environment helper (inside `settings.py`)

A helper function `env_get(key, default, cast, required)` was implemented directly in `backend/backend/settings.py` (no external `conf.py`).

**Cast support:**

| `cast` value | Behaviour |
|---|---|
| `str` (default) | Raw stripped string |
| `int` / `float` | Numeric conversion; raises `RuntimeError` on failure |
| `bool` | Accepts `true/false/1/0/yes/no/on/off` (case-insensitive) |
| `list` | Comma-separated; each item stripped, empty items removed |

**Error behaviour:**

- `required=True` with a missing/empty variable → `RuntimeError` with a clear message pointing to `.env`.
- Cast failure → `RuntimeError` showing key, raw value, and target type.

### 3. Path resolution with `pathlib`

```python
BASE_DIR = Path(__file__).resolve().parent.parent   # WP-Project/backend/
ROOT_DIR = Path(__file__).resolve().parents[2]      # WP-Project/
load_dotenv(ROOT_DIR / ".env")
```

`parents[2]` reliably walks up from `backend/backend/settings.py` to the repo root regardless of the working directory when Django is started.

### 4. All relevant settings now use `env_get`

| Setting | Variable | Cast | Required | Default |
|---|---|---|---|---|
| `SECRET_KEY` | `SECRET_KEY` | `str` | ✅ | — |
| `DEBUG` | `DEBUG` | `bool` | — | `False` |
| `ALLOWED_HOSTS` | `ALLOWED_HOSTS` | `list` | — | `["localhost","127.0.0.1"]` |
| `CSRF_TRUSTED_ORIGINS` | `CSRF_TRUSTED_ORIGINS` | `list` | — | `["http://localhost:5173"]` |
| `CORS_ALLOWED_ORIGINS` | `CORS_ALLOWED_ORIGINS` | `list` | — | `["http://localhost:5173"]` |
| `DATABASES['default']` | `DB_NAME`, `DB_USER`, `DB_PASSWORD` | `str` | ✅ | — |
| | `DB_HOST`, `DB_PORT` | `str` | — | `localhost`, `5432` |
| `LANGUAGE_CODE` | `LANGUAGE_CODE` | `str` | — | `en-us` |
| `TIME_ZONE` | `TIME_ZONE` | `str` | — | `UTC` |
| `STATIC_URL` / `STATIC_ROOT` | `STATIC_URL`, `STATIC_ROOT` | `str` | — | `/static/`, `staticfiles` |
| `MEDIA_URL` / `MEDIA_ROOT` | `MEDIA_URL`, `MEDIA_ROOT` | `str` | — | `/media/`, `media` |
| `LOG_LEVEL` | `LOG_LEVEL` | `str` | — | `INFO` |

### 5. PostgreSQL — SQLite removed

The `DATABASES` dict now uses `django.db.backends.postgresql` exclusively. SQLite was removed to prevent accidental local-only data that diverges from staging/production.

### 6. WhiteNoise

- `whitenoise>=6.7.0` added to `requirements.txt`.
- `WhiteNoiseMiddleware` inserted **immediately after** `SecurityMiddleware` (required position).
- `STORAGES` dict updated to use `whitenoise.storage.CompressedManifestStaticFilesStorage` (Django 4.2+ API).
- `STATIC_ROOT` defaults to `BASE_DIR / "staticfiles"` so `python manage.py collectstatic` works out of the box.

### 7. CORS middleware placement fixed

`corsheaders.middleware.CorsMiddleware` is now correctly placed **before** `CommonMiddleware` in `MIDDLEWARE`, which is required for it to handle pre-flight `OPTIONS` requests.

### 8. Vite `envDir`

`frontend/vite.config.ts` now sets:

```ts
envDir: path.resolve(__dirname, '..')
```

This points Vite at `WP-Project/` so it reads `WP-Project/.env`. Only variables prefixed with `VITE_` are exposed to client-side code (e.g., `import.meta.env.VITE_API_BASE_URL`).

---

## Files Created / Modified

| File | Action |
|---|---|
| `WP-Project/.env.example` | **Created** — safe template, no secrets |
| `WP-Project/backend/requirements.txt` | **Modified** — added `python-dotenv>=1.0.0`, `whitenoise>=6.7.0` |
| `WP-Project/backend/backend/settings.py` | **Rewritten** — dotenv loading, `env_get`, all settings migrated, WhiteNoise, CORS fix |
| `WP-Project/frontend/vite.config.ts` | **Modified** — added `envDir` pointing to repo root |

`.gitignore` was already correct (`.env` ignored, `.env.example` tracked).

---

## How to Run Locally (no `export` needed)

```bash
# 1. Copy and fill in the template
cp WP-Project/.env.example WP-Project/.env
# Edit WP-Project/.env — set SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD

# 2. Install Python deps
cd WP-Project/backend
pip install -r requirements.txt

# 3. Start Django
python manage.py migrate
python manage.py collectstatic --no-input   # writes to backend/staticfiles/
python manage.py runserver

# 4. Start Vite (separate terminal)
cd WP-Project/frontend
npm install
npm run dev
```

---

## Pitfalls & Notes

### CSRF / CORS

- `CSRF_TRUSTED_ORIGINS` must include the **full scheme + host** (e.g., `http://localhost:5173`), not just the hostname.
- `CORS_ALLOWED_ORIGINS` requires the same format.
- If new frontend origins are added (e.g., `https://app.example.com`), add them to **both** variables in `.env`.

### `STATIC_ROOT` and `collectstatic`

- `STATIC_ROOT` must be set before running `collectstatic`.
- `CompressedManifestStaticFilesStorage` hashes file names at collection time. If you delete `staticfiles/` and forget to re-run `collectstatic`, Django will raise `ValueError: Missing staticfiles manifest entry`.
- In development (`DEBUG=true`), WhiteNoise still works but the manifest storage requires `collectstatic` to have been run at least once. For pure development you can swap to `whitenoise.storage.CompressedStaticFilesStorage` (no manifest) if needed.

### `bool` / `list` parsing

- `DEBUG=True` (capital T) is valid; so is `DEBUG=1` or `DEBUG=yes`.
- `ALLOWED_HOSTS=localhost,127.0.0.1` — no spaces required around commas, but they are trimmed if present.
- An empty string value (e.g., `LOG_LEVEL=`) is treated the same as "not set" and falls back to the default.

### Vite `VITE_` prefix requirement

Vite deliberately strips any variable that does **not** start with `VITE_` from `import.meta.env` to prevent accidental secret leakage. Django-only variables (e.g., `SECRET_KEY`, `DB_PASSWORD`) are never accessible in the browser even though they live in the same `.env` file.

### `python-dotenv` `load_dotenv` behaviour

`load_dotenv` does **not** overwrite variables that are already set in the environment. This means Docker Compose (which injects vars via `env_file`) takes precedence over the file — the same `.env` can be used for both local dev and Docker without conflict.
