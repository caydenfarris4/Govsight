# GovSight Financial Intelligence Platform - full stack container
# Runs the Streamlit application (port 5000), the PBB FastAPI backend
# (port 8000, internal), and the Budget Playground Node API (port 5002,
# internal, reverse-proxied by the app at /bp-api).
FROM python:3.11-slim

WORKDIR /app

# System dependencies: libpq for psycopg2, nodejs for the Budget Playground API
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY budget_playground_api/package.json budget_playground_api/
RUN cd budget_playground_api && npm install --omit=dev

COPY . .

# Databases live here; mount a volume to persist GL data, scenarios,
# audit logs, and user databases across restarts.
RUN mkdir -p databases/core

EXPOSE 5000

ENV PYTHONUNBUFFERED=1

CMD ["bash", "scripts/start_all.sh"]
