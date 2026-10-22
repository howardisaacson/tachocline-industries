# Tachocline Industries

*Real-time satellite and space-weather data: from the Sun's interior to the satellites it drags out of the sky.*

Tachocline Industries (TI) is a portfolio project by **Howard Isaacson** (astronomy and data, UC Berkeley; California Planet Search). It ingests live, open satellite data streams, stores them in a time-series database, and presents them through dashboards and a web site. Every page explains how it works, and every technical choice is documented.

> The **tachocline** is the shear layer at the base of the Sun's convection zone, thought to drive the solar dynamo. That dynamo powers the activity this site tracks: sunspots, flares, CMEs, and solar wind, and their effects on Earth and on satellites.

## Goals
1. **Job-search portfolio** for data engineering, data science, and software engineering roles. It shows a real end-to-end system: ingestion → storage → API → visualisation → (later) cloud deployment.
2. **Learn by building**, with full understanding: databases, Grafana, APIs, JavaScript/React, service architecture, cloud, and Rust. Every decision is recorded as an [ADR](docs/decisions/README.md), and every page has an ["About this page"](docs/about-this-page-template.md).
3. **Add scientific value** beyond plotting feeds: e.g., how solar activity inflates the thermosphere and shortens satellite lifetimes, and the Sun compared with other stars ([ideas](docs/ideas.md)).

## Current status (2026-10-20)
- ✅ Data-source research: [docs/research/data_sources.md](docs/research/data_sources.md)
- ✅ ADR process accepted ([0001](docs/decisions/0001-record-architecture-decisions.md)); ADRs 0002–0018 **Proposed**, awaiting review
- ⏳ Next: Phase 0/1 of the [roadmap](docs/ROADMAP.md): GitHub repo, Docker Compose, first feed (NOAA SWPC solar wind) end to end
- No application code yet

## Planned stack (all Proposed)
Python pollers (APScheduler) → PostgreSQL + TimescaleDB → FastAPI → Grafana now, React later, run locally with Docker Compose. See [AGENTS.md](AGENTS.md#stack-summary) for the table with ADR links.

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
*Coming in Phase 1.* It will be: install Docker → `cp .env.example .env` → `docker compose up`.

## Data credits
NOAA Space Weather Prediction Center, CelesTrak / 18th Space Defense Squadron, NASA (FIRMS, CMR, SDO, DONKI), ESA Copernicus, SatNOGS / Libre Space Foundation. See the research doc for details.
