# ── Backend Dockerfile ────────────────────────────────────────────────────────
# Base: python:3.12-slim
# Installs system deps needed by psycopg2-binary (libpq) and Pillow (libjpeg).
# Source code is NOT copied at build time for local dev — it is volume-mounted
# by docker-compose so changes are immediately reflected without rebuilding.
# .env is intentionally NOT copied into the image.

FROM python:3.12-slim

# System deps
# libpq-dev + gcc  → psycopg2-binary build support
# libjpeg-dev      → Pillow JPEG support
# netcat-openbsd   → used in entrypoint for DB readiness check
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libjpeg-dev \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Install Python dependencies first (cached layer)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy and set up entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
