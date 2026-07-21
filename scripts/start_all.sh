#!/usr/bin/env bash
# Start the full GovSight stack: PBB API (8000), Budget Playground API (5002),
# and the Streamlit application (5000, or $PORT if set).
#
# Used as the container entrypoint and for local development:
#   bash scripts/start_all.sh
#
# Optional environment variables:
#   PORT              Streamlit port (default 5000)
#   SEED_SAMPLE_DATA  Set to 1 to seed a sample GL database if none exists
#   PBB_API_URL       Browser-facing URL of the PBB API (defaults to
#                     http://localhost:8000 for local development)
set -e
cd "$(dirname "$0")/.."

PORT="${PORT:-5000}"

if [ "${SEED_SAMPLE_DATA:-0}" = "1" ] && [ ! -f databases/core/govsight_all_in_one_data.db ]; then
    echo "Seeding sample GL database..."
    python3 scripts/seed_sample_gl.py
fi

echo "Starting PBB API on port 8000..."
python3 modules/api/pbb_api.py &

if command -v node >/dev/null 2>&1 && [ -d budget_playground_api/node_modules ]; then
    echo "Starting Budget Playground API on port 5002..."
    (cd budget_playground_api && node server.js) &
else
    echo "Skipping Budget Playground API (node or node_modules not available)"
fi

echo "Starting Streamlit application on port ${PORT}..."
exec python3 -m streamlit run modules/core/main_app.py \
    --server.port "${PORT}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
