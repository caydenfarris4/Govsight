#!/usr/bin/env bash
# Start the GovSight platform stack:
#
#   - Platform API + SPA (uvicorn, port 8000) - the public entrypoint.
#     Serves the bundled React application and every API (auth, data
#     bundle, budget playground at /api/bp, Mantis chat, PBB, treasury).
#   - Management console (Streamlit, port 5000 or $PORT) - admin surface:
#     user management, ERP integration hub, AI data mapping, settings.
#
# The standalone Budget Playground Node API is retired - its endpoints
# were ported into the platform API under /api/bp. It is only started
# when its node_modules are present (legacy support for the Streamlit
# Budget tab during local development).
#
# Usage:
#   bash scripts/start_all.sh
#
# Environment variables:
#   API_PORT          Platform API/SPA port (default 8000)
#   PORT              Management console port (default 5000)
#   SESSION_SECRET    HMAC secret for platform session cookies (set in prod)
#   SEED_SAMPLE_DATA  Set to 1 to seed a sample GL database if none exists
#   PBB_API_URL       Browser-facing URL of the platform API (defaults to
#                     http://localhost:8000 for local development)
set -e
cd "$(dirname "$0")/.."

PORT="${PORT:-5000}"
API_PORT="${API_PORT:-8000}"

if [ "${SEED_SAMPLE_DATA:-0}" = "1" ] && [ ! -f databases/core/govsight_all_in_one_data.db ]; then
    echo "Seeding sample GL database..."
    python3 scripts/seed_sample_gl.py
fi

# Build the SPA if it isn't built yet and a toolchain is available
# (the Docker image ships it prebuilt from the frontend build stage)
if [ ! -f frontend/dist/index.html ] && command -v npm >/dev/null 2>&1; then
    echo "Building frontend bundle..."
    (cd frontend && npm ci && npm run build)
fi

echo "Starting GovSight platform (SPA + APIs) on port ${API_PORT}..."
python3 -m uvicorn modules.api.pbb_api:app --host 0.0.0.0 --port "${API_PORT}" &

if command -v node >/dev/null 2>&1 && [ -d budget_playground_api/node_modules ]; then
    echo "Starting legacy Budget Playground API on port 5002..."
    (cd budget_playground_api && node server.js) &
fi

echo "Starting management console (Streamlit) on port ${PORT}..."
exec python3 -m streamlit run modules/core/main_app.py \
    --server.port "${PORT}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
