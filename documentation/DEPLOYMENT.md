# GovSight Deployment Guide

GovSight has two deployable pieces with different hosting requirements:

| Piece | What it is | Where it runs |
|---|---|---|
| Static front-door (`public/`) | Login-gated demo app: the self-contained browser tools and data views over the bundled sample city | Cloudflare Workers static assets |
| Full platform | React SPA + unified FastAPI backend (auth, live data bundle, budget playground, Mantis AI, treasury, PBB) plus the Streamlit management console | Any container host (Docker, Google Cloud Run) |

Cloudflare's static hosting cannot run long-lived Python servers, so the full
platform must be hosted on a server or container platform. Cloudflare can sit
in front of it as DNS/proxy, and the static demo deploys to Workers directly.

## 0. Fastest path: git-connected container host (demo deployment)

The repo is deploy-ready for any host that builds a Dockerfile from
GitHub and routes one HTTPS port to it. `GOVSIGHT_MODE=platform` makes
the container serve the platform (SPA + all APIs) on the injected
`$PORT`, skipping the Streamlit console and legacy Node API to fit
small instances.

**Render** (about two clicks): dashboard.render.com > New > Blueprint >
pick this repo. `render.yaml` configures everything - Docker build,
`/health` checks, demo data seeding, a generated `SESSION_SECRET`. Use
an instance with at least 1 GB RAM.

**Railway**: railway.app > New Project > Deploy from GitHub repo. It
auto-detects the Dockerfile; set environment variables
`GOVSIGHT_MODE=platform` and `SEED_SAMPLE_DATA=1`, plus a strong
`SESSION_SECRET`, then Generate Domain.

**Google Cloud Run**: `gcloud run deploy govsight --source . --memory 2Gi
--set-env-vars GOVSIGHT_MODE=platform,SEED_SAMPLE_DATA=1,SESSION_SECRET=...`
(see scripts/deploy.sh for the scripted version).

After first boot, sign in with the default admin credentials, then use
Admin > Platform > AI Provider Keys to enable Mantis chat and insights.

Demo-deployment caveat: these hosts give containers ephemeral disks, so
admin changes and synced data reset on each redeploy (the demo city
reseeds automatically). For a production city, attach a persistent
volume or move the data layer to a managed database first.

## 1. Full platform (the real product)

Two services on one host:

- **Platform (SPA + APIs)** — uvicorn on port 8000, the public entrypoint.
  Serves the bundled React application at `/` and every API under `/api/*`:
  auth (`/api/auth`), live data bundle (`/api/data`), budget playground
  (`/api/bp`), Mantis chat (`/api/mantis`), plus the PBB, grants,
  Monte Carlo, investment, and portfolio endpoints.
- **Management console** — Streamlit on port 5000: user management, ERP
  integration hub, AI data mapping review, system settings, report
  scheduler. Restrict this port to administrators in production.

The standalone Budget Playground Node API is retired; its endpoints were
ported into the platform API under `/api/bp`.

Run everything with:

```bash
docker compose up --build
```

or without Docker:

```bash
pip install -r requirements.txt
(cd frontend && npm ci && npm run build)
SEED_SAMPLE_DATA=1 bash scripts/start_all.sh
```

Then open http://localhost:8000 (platform) and http://localhost:5000
(management console). Default logins are configured in
`modules/admin/user_database.py`; change them before real use.

### Frontend build

`frontend/` is a Vite + React application. The Scenario Planner, Budget
Playground, and Investment Optimizer are precompiled into the bundle by
`scripts/extract_frontend_tools.py` (generated files under
`frontend/src/tools/` and `frontend/src/vendor/`). After editing the
source HTML tools or `public/assets/demo_views.js` /
`public/assets/bi_sandbox.js`, re-run:

```bash
python3 scripts/extract_frontend_tools.py
(cd frontend && npm run build)
```

The Docker image builds the frontend in its own stage; nothing to do there.

### Environment variables

| Variable | Purpose |
|---|---|
| `API_PORT` | Platform port (default 8000) |
| `PORT` | Management console port (default 5000) |
| `SESSION_SECRET` | HMAC secret for platform session cookies — set a strong value in production |
| `OPENAI_API_KEY` | Enables Mantis AI features (GPT models) |
| `ANTHROPIC_API_KEY` | Enables Mantis dual-AI routing (Claude models) |
| `SEED_SAMPLE_DATA=1` | Seeds a sample GL database on first start if none exists |
| `PBB_API_URL` | Browser-facing URL of the platform API (required behind a proxy) |
| `GOVSIGHT_INSECURE_COOKIES=1` | Allow session cookies over plain HTTP (local development only) |

### Data

The GL database (`databases/core/govsight_all_in_one_data.db`) is not in the
repository. Either seed sample data (`SEED_SAMPLE_DATA=1` or
`python3 scripts/seed_sample_gl.py`) or load real data through the ERP
integration hub (AI data mapping) in the management console. Mount a volume
at `/app/databases` to persist data across container restarts.

The platform serves whatever is live and labels the rest: `/api/data/bundle`
marks each section `live` or `sample` in `meta.sources`, and the UI shows a
LIVE DATA banner listing the live sections.

### Tests

```bash
python3 -m pytest modules/testing -q            # unit tests (engines, mappers)
python3 -m pytest tests/e2e/test_spa_e2e.py -q  # SPA end-to-end (needs a running platform)
python3 -m pytest tests/e2e/test_platform_e2e.py -q  # management console e2e
```

## 2. Cloudflare (static demo front-door)

The repository is Workers-ready:

- `wrangler.toml` sets the static assets directory to `public/`.
- `worker/index.js` gates the demo behind the login page with a signed
  cookie.
- No build command is needed; `public/` is committed prebuilt.

Every push to the connected branch redeploys. The demo app runs the same
views as the platform against the bundled sample city
(`public/demo/demo_data.json`); views that defer to platform engines fall
back to their in-browser models and are badged IN-BROWSER MODEL.

## 3. Putting Cloudflare in front of the platform

Point a DNS record (e.g. `app.yourdomain.com`) at the host running the
container, proxied through Cloudflare, forwarding to port 8000. That one
port serves the SPA and all APIs — no separate API hostname is needed.
Expose the management console (port 5000) on a restricted hostname or keep
it VPN-only; set `PBB_API_URL=https://app.yourdomain.com` so the console's
embedded tools call the platform correctly.

Alternative: Google Cloud Run deployment scripts and docs exist in
`scripts/deploy.sh`, `scripts/setup_gcp.sh`, and
`documentation/GOOGLE_CLOUD_DEPLOYMENT.md`; Cloudflare then just fronts the
Cloud Run URL.

## Security checklist before going live

- Set `SESSION_SECRET` to a strong random value (both the edge worker and
  the platform sign session cookies with it).
- Rotate the Google service account key that previously lived in
  `configs/system/system_settings.json` (it was redacted from the repo but
  the key itself should be considered exposed).
- Change the default user passwords (`govsight123`) and the
  `DefaultPassword` in `configs/system/system_settings.json`.
- Provide AI keys via environment variables or a secret manager, never in
  config files.
- `configs/security/.encryption_key` is generated per deployment and is
  gitignored; do not commit it.
- Serve over HTTPS and do not set `GOVSIGHT_INSECURE_COOKIES` in
  production.
