# GovSight Deployment Guide

GovSight has two deployable pieces with different hosting requirements:

| Piece | What it is | Where it runs |
|---|---|---|
| Static front-door (`public/`) | Landing page plus the self-contained browser tools (Scenario Planner, Investment Optimizer, Budget Playground UI) | Cloudflare Pages |
| Full platform | Streamlit application with authentication, databases, AI features, and two backend APIs | Any container host (Docker, Google Cloud Run) |

Cloudflare Pages cannot run long-lived Python or Node servers, so the full
platform must be hosted on a server or container platform. Cloudflare can sit
in front of it as DNS/proxy, and the static tools deploy to Pages directly.

## 1. Cloudflare Pages (static tools)

The repository is Pages-ready:

- `wrangler.toml` sets `pages_build_output_dir = "public"`.
- No build command is needed; `public/` is committed prebuilt.

In the Cloudflare Pages project settings, leave the build command empty and
set the output directory to `public` (or rely on `wrangler.toml`). Every push
to the connected branch redeploys the site.

What works on Pages: the Scenario Planner and Investment Optimizer are fully
client-side (state in localStorage, shareable links via URL hash). The Budget
Playground UI loads, but needs its API to show data — set a public URL for it
or host the full platform.

## 2. Full platform (Docker)

The platform is three processes on one host, matching the original Replit
layout:

- Streamlit application — port 5000 (the only public port)
- PBB FastAPI backend (`modules/api/pbb_api.py`) — port 8000
- Budget Playground Node API (`budget_playground_api/server.js`) — port 5002,
  reverse-proxied by the app itself at `/bp-api` (see `modules/navi/bp_proxy.py`)

Run everything with:

```bash
docker compose up --build
```

or without Docker:

```bash
pip install -r requirements.txt
cd budget_playground_api && npm install && cd ..
SEED_SAMPLE_DATA=1 bash scripts/start_all.sh
```

Then open http://localhost:5000 (default admin login is configured in
`modules/admin/user_database.py`; change it before real use).

### Environment variables

| Variable | Purpose |
|---|---|
| `PORT` | Streamlit port (default 5000) |
| `OPENAI_API_KEY` | Enables Mantis AI features (GPT models) |
| `ANTHROPIC_API_KEY` | Enables Mantis dual-AI routing (Claude models) |
| `SEED_SAMPLE_DATA=1` | Seeds a sample GL database on first start if none exists |
| `PBB_API_URL` | Browser-facing URL of the PBB API (required behind a proxy; see below) |

### Data

The GL database (`databases/core/govsight_all_in_one_data.db`) is not in the
repository. Either seed sample data (`SEED_SAMPLE_DATA=1` or
`python3 scripts/seed_sample_gl.py`) or load real data through the Caselle
adapter / file importer in `modules/data_adapter/`. Mount a volume at
`/app/databases` to persist data across container restarts.

## 3. Putting Cloudflare in front of the platform

Point a DNS record (e.g. `app.yourdomain.com`) at the host running the
container, proxied through Cloudflare. Two ports matter:

- Port 5000 serves everything the app itself needs, including `/bp-api`.
- Port 8000 (PBB API) is called directly from the browser by the Scenario
  Planner and PBB tabs. Behind Cloudflare, expose it on its own hostname
  (e.g. `pbb.yourdomain.com` -> host port 8000) and set
  `PBB_API_URL=https://pbb.yourdomain.com` so the app injects the right URL.

Alternative: Google Cloud Run deployment scripts and docs already exist in
`scripts/deploy.sh`, `scripts/setup_gcp.sh`, and
`documentation/GOOGLE_CLOUD_DEPLOYMENT.md`; Cloudflare then just fronts the
Cloud Run URL.

## Security checklist before going live

- Rotate the Google service account key that previously lived in
  `configs/system/system_settings.json` (it was redacted from the repo but
  the key itself should be considered exposed).
- Change the default user passwords (`govsight123`) and the
  `DefaultPassword` in `configs/system/system_settings.json`.
- Provide AI keys via environment variables or a secret manager, never in
  config files.
- `configs/security/.encryption_key` is generated per deployment and is
  gitignored; do not commit it.
