# GovSight Financial Intelligence Platform - full stack container
#
# Stage 1 builds the React SPA; stage 2 is the Python runtime that
# serves it. Two services run in the container:
#   - Platform API + SPA (uvicorn, port 8000) - public entrypoint
#   - Management console (Streamlit, port 5000) - admin surface
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

# libpq for psycopg2 (optional Postgres connections)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /build/dist frontend/dist

# Databases live here; mount a volume to persist GL data, scenarios,
# audit logs, and user databases across restarts.
RUN mkdir -p databases/core

EXPOSE 8000 5000

ENV PYTHONUNBUFFERED=1

CMD ["bash", "scripts/start_all.sh"]
