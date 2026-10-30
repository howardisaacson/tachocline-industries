# Tachocline Industries

*Real-time satellite and space-weather data: from the Sun's interior to the satellites it drags out of the sky.*

Tachocline Industries (TI) is a portfolio project by **Howard Isaacson** (astronomy and data, UC Berkeley; California Planet Search). It ingests live, open satellite data streams, stores them in a time-series database, and presents them through dashboards and a web site. Every page explains how it works, and every technical choice is documented.

> The **tachocline** is the shear layer at the base of the Sun's convection zone, thought to drive the solar dynamo. That dynamo powers the activity this site tracks: sunspots, flares, CMEs, and solar wind, and their effects on Earth and on satellites.

## Goals
1. **Job-search portfolio** for data engineering, data science, and software engineering roles. It shows a real end-to-end system: ingestion → storage → API → visualisation → (later) cloud deployment.
2. **Learn by building**, with full understanding: databases, Grafana, APIs, JavaScript/React, service architecture, cloud, and Rust. Every decision is recorded as an [ADR](docs/decisions/README.md), and every page has an ["About this page"](docs/about-this-page-template.md).
3. **Add scientific value** beyond plotting feeds: e.g., how solar activity inflates the thermosphere and shortens satellite lifetimes, and the Sun compared with other stars ([ideas](docs/ideas.md)).

## Current status (2026-10-25)
- ✅ Data-source research: [docs/research/data_sources.md](docs/research/data_sources.md)
- ✅ ADR process accepted ([0001](docs/decisions/0001-record-architecture-decisions.md)); ADRs [0001–0023](docs/decisions/README.md) are **Accepted**
- ✅ Local Compose stack: TimescaleDB, a one-shot `migrate`, the SWPC `ingest` poller, and Grafana.
- ✅ First SQL migration: `solar_wind` and `rtsw_mag_1m` hypertables, `ingest_log`, and a read-only role (issue #25). [ADR 0019](docs/decisions/0019-apply-sql-migrations-in-order.md) (how `migrate` applies SQL) is **Accepted**.
- ✅ SWPC poller writes `rtsw_wind_1m` and `rtsw_mag_1m` into `data/raw/swpc_rtsw/<date>/`, validates each row, and upserts `solar_wind` and `rtsw_mag_1m` on `(time_tag, source)`. One `ingest_log` row is written per file attempted (issues #26 and #27).
- ✅ GOES X-ray flux: the same process also fetches `xrays-6-hour.json` into `data/raw/goes_xray/<date>/` and upserts `goes_xray_flux` on `(time_tag, satellite, energy)` (issue #31). The Solar wind dashboard charts the 0.1–0.8 nm channel on a log axis. About: [docs/about/goes-xray.md](docs/about/goes-xray.md).
- ✅ Grafana dashboard **Solar wind**, provisioned from [`dashboards/`](dashboards/json/solar-wind.json) (issue #28): proton speed, density, Bz for the active spacecraft, and minutes since the last good `ingest_log` row. The datasource logs in as `TI_READONLY_USER` (SELECT only). A live look in a narrow browser window is still open; the limit is written on the dashboard.
- ✅ About page for the solar-wind dashboard: [docs/about/solar-wind.md](docs/about/solar-wind.md) (issue #30), linked from the Grafana dashboard.
- ⏳ Next: a live browser check of that dashboard in a narrow window is still open (issue #28). See the [roadmap](docs/ROADMAP.md).

## Planned stack
Python pollers (APScheduler) → PostgreSQL + TimescaleDB → FastAPI → Grafana now, React later, run locally with Docker Compose. See [AGENTS.md](AGENTS.md#stack-summary) for the table with ADR links. ADRs 0001–0023 are Accepted.

## Documentation
| Doc | What |
|---|---|
| [AGENTS.md](AGENTS.md) | Rules for AI coding agents *and* humans contributing |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phased milestones |
| [docs/ideas.md](docs/ideas.md) | Product and science ideas backlog |
| [docs/data-science-workflow.md](docs/data-science-workflow.md) | End-to-end data science workflow (Drag Watch example) |
| [docs/ai-agents.md](docs/ai-agents.md) | AI agents: building with them and features in the product |
| [docs/links.md](docs/links.md) | Relevant articles and news (newest first) |
| [docs/github-workflow.md](docs/github-workflow.md) | How work is planned and tracked: Issues, Milestones, Project, PRs |
| [Issues](https://github.com/howardisaacson/tachocline-industries/issues) · [Milestones](https://github.com/howardisaacson/tachocline-industries/milestones) | Live status of the roadmap |
| [docs/decisions/](docs/decisions/README.md) | Architecture Decision Records |
| [docs/research/](docs/research/) | Research notes (data sources, design survey, satellite orbit decay data) |
| [docs/about-this-page-template.md](docs/about-this-page-template.md) | Template for each page's About section |

## Quick start
Install [Docker](https://docs.docker.com/get-started/get-docker/), then from this directory:

```bash
cp .env.example .env
# edit the passwords in .env; do not commit that file
docker compose up --build
```

- API: `http://127.0.0.1:8000/docs` (host port `API_PORT`, default 8000). Read-only. The container logs in as `TI_READONLY_USER`. See [docs/about/api.md](docs/about/api.md).
- Public page: `http://127.0.0.1:8080` (host port `WEB_PORT`, default 8080). Three radial Kp plots. The container proxies `/api` to the API. See [docs/about/space-weather.md](docs/about/space-weather.md). Rebuild after a frontend change: `docker compose up -d --build web`.
- Grafana: `http://127.0.0.1:3000` (user and password are `GF_SECURITY_ADMIN_USER` and `GF_SECURITY_ADMIN_PASSWORD` in `.env`). The **Solar wind** dashboard is loaded from `dashboards/`. After this file changes, recreate the container so it sees the new mounts and environment: `docker compose up -d grafana`. Edits to the dashboard JSON are picked up within 30 seconds. On a phone-width window the panels stack (each is a full-width row). Grafana's own menu and time picker stay, and the charts do not switch to a simplified axis, so below 640 px the page is tall and the menu can crowd a 320 px window.
- Postgres: `127.0.0.1` and `POSTGRES_PORT` from `.env`. The data directory is the Docker named volume `pgdata`, not a folder in this repo.
- `ingest` fetches the two solar-wind files and `xrays-6-hour.json` on startup and then every `SWPC_POLL_MINUTES`. Raw JSON lands in `data/raw/swpc_rtsw/` and `data/raw/goes_xray/`, which git ignores. Valid rows are upserted into `solar_wind`, `rtsw_mag_1m`, and `goes_xray_flux`. `migrate` applies the numbered files in `db/migrations/`, then exits. Copy `TI_READONLY_USER` and `TI_READONLY_PASSWORD` from `.env.example` into `.env` before the first migrate. Those two values are local-dev only.
- After adding a SQL file, run `docker compose up --force-recreate migrate`. A one-shot container that already exited successfully is not run again by a plain `docker compose up`.

## Data credits
NOAA Space Weather Prediction Center, CelesTrak / 18th Space Defense Squadron, NASA (FIRMS, CMR, SDO, DONKI), ESA Copernicus, SatNOGS / Libre Space Foundation. See the research doc for details.
