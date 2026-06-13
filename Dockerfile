# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the React/Vite frontend -> frontend/dist
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend

WORKDIR /build/frontend

# Install deps first (better layer caching) then build.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
# Output: /build/frontend/dist

# ---------------------------------------------------------------------------
# Stage 2: Python runtime serving the API + the built frontend
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# - PYTHONUNBUFFERED so logs flush immediately (useful for Fly/Railway logs)
# - PORT default; Fly and Railway inject their own $PORT at runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Copy the Python sources and project metadata.
# NOTE on layout: app.py computes FRONTEND_DIST as parents[2]/frontend/dist
# relative to backend/wc2026_backend/app.py. We therefore install the package
# in EDITABLE mode (pip install -e) so the source stays at
# /app/backend/wc2026_backend/app.py, which makes parents[2] == /app, and we
# place the built frontend at /app/frontend/dist. A non-editable install would
# move app.py into site-packages and break that relative path.
COPY pyproject.toml ./
COPY engine/ ./engine/
COPY backend/ ./backend/

RUN pip install --no-cache-dir -e .[supabase]

# Bring in the compiled frontend from stage 1 at the path app.py expects.
COPY --from=frontend /build/frontend/dist ./frontend/dist

EXPOSE 8080

# Shell form so $PORT expands at runtime (Fly/Railway provide it; default 8080).
# `exec` replaces the shell with uvicorn so it gets SIGTERM directly — this lets
# the FastAPI lifespan run its shutdown (stop the live poller, close the store)
# cleanly when the platform stops the container.
CMD exec uvicorn wc2026_backend.app:app --host 0.0.0.0 --port ${PORT:-8080}
