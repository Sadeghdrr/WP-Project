# ── Frontend Dockerfile (dev) ─────────────────────────────────────────────────
# Base: node:20-alpine
#
# Only npm dependencies are installed at build time.
# The actual source code (src/, public/, vite.config.ts, …) is volume-mounted
# by docker-compose, which enables Vite hot-module-replacement (HMR) without
# image rebuilds.
#
# .env is intentionally NOT copied. Vite reads env vars from /app/.env
# at runtime thanks to `envDir: path.resolve(__dirname, '..')` in vite.config.ts.

FROM node:20-alpine

WORKDIR /app/frontend

# Install dependencies (cached layer; this layer is invalidated only when
# package.json or package-lock.json change)
COPY package.json package-lock.json ./
RUN npm ci

EXPOSE 5173
