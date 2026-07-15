# PACOS cloud image: one container serves the API *and* the built dashboard,
# mirroring the frozen-exe layout (ADR 0004) — FastAPI mounts frontend/dist
# with an SPA fallback, so there is no separate frontend host and no CORS.
# Workspace state (leads.csv, tracker.db, output/) lives on a mounted volume;
# point the *_PATH env vars at it (see render.yaml / docs/DEPLOYMENT.md).

# ── Stage 1: build the React dashboard ──────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ─────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Editable install keeps the package at /app/src, so config.py resolves the
# repo root to /app — same layout as a source checkout.
COPY pyproject.toml README.md ./
COPY src ./src
COPY backend ./backend
RUN pip install --no-cache-dir -e . -r backend/requirements.txt

COPY --from=frontend /build/dist ./frontend/dist

# Non-root runtime user (uid 1000 — required by Hugging Face Spaces, good
# hygiene everywhere). /app must stay writable: the workspace defaults
# (data/leads.csv, tracker.db, output/) live under it when no *_PATH env
# vars point elsewhere.
RUN useradd -m -u 1000 pacos \
    && mkdir -p /app/data /app/output \
    && chown -R pacos:pacos /app
USER pacos
ENV HOME=/home/pacos

EXPOSE 8000
# Shell form so $PORT (injected by Render/Railway/Fly) expands.
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
