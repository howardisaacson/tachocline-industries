# AGENTS.md: master instructions for AI coding agents (and humans)

This is the **single source of truth** for how to work in this repo. `CLAUDE.md`, `GROK.md`, and `.cursor/rules/agents.mdc` only point here. If anything conflicts, this file wins; update it in a PR rather than working around it.

## 1. Project purpose
Tachocline Industries (TI) is Howard Isaacson's portfolio site. It ingests real-time open satellite and space-weather data, stores it, and presents it through dashboards and a website. See [README.md](README.md), [docs/ROADMAP.md](docs/ROADMAP.md), [docs/ideas.md](docs/ideas.md).

## 2. Howard is learning, so teach, don't just generate
Howard has a strong astronomy, data and Python background and is **learning**: databases, Grafana, JavaScript, React, microservices and service design, APIs, cloud, and Rust. He must be able to **explain every part of this system in a job interview**. So:
- **Explain your reasoning** before or alongside code: what you're doing, why, and what the alternatives were.
- **Teach the concept** the first time it appears (e.g., "an upsert is…", "a React hook is…"), briefly and in plain language, with one link to official docs.
- Prefer **simple, readable, idiomatic code** over clever code. No magic he can't explain.
- Keep changes **small and reviewable**. Don't scaffold large frameworks or many files at once without asking.
- When a task touches something new, end your reply with **"How to explain this in an interview"** (2–3 sentences) and, where useful, a question Howard could be asked about it.
- If the request is ambiguous or implies a significant decision, **ask or propose an ADR** instead of silently choosing.
- Never claim something works without running it; say what you tested.

## 3. Architecture Decision Records (mandatory)
- Every **significant decision** (hard to reverse, affects several parts, or something an interviewer could ask "why X?" about) gets an ADR in [`docs/decisions/`](docs/decisions/README.md), using the template there. Number sequentially and add it to the index table.
- New ADRs are **Proposed**. Only Howard marks them **Accepted**.
- **Never edit the decision of an Accepted ADR.** Write a new ADR that **supersedes** it, and update the status line on both (typo and link fixes are fine).
- Code must follow Accepted ADRs. If code needs to diverge, write the ADR first.
- "Learn more" links must be real and checked; prefer official documentation.

## 4. "About this page" (mandatory)
- Every page, dashboard, or section ships with an accurate **About this page** written from [`docs/about-this-page-template.md`](docs/about-this-page-template.md), stored at `docs/about/<page-slug>.md` and linked from the page ([ADR 0009](docs/decisions/0009-about-this-page-for-every-section.md)).
- Any PR that changes a page's data source, pipeline, tech, or limitations **updates its About page in the same PR**. A feature isn't done without it.

## 5. Mobile and desktop specs (mandatory for all UI)
Per [ADR 0012](docs/decisions/0012-responsive-design-mobile-and-desktop.md):
- Design **mobile-first**; every page spec states its layout at each breakpoint:

  | Name | Width | Typical device |
  |---|---|---|
  | `mobile` | < 640 px | phones (test at 375 px and 390 px) |
  | `tablet` | 640–1023 px | small tablets, landscape phones |
  | `desktop` | ≥ 1024 px | laptops/desktops (test at 1280 px and 1440 px) |

- No horizontal scrolling at 320 px. Tap targets are at least 44×44 px. Charts must stay readable on mobile (fewer series, simplified axes, or stacked). Respect `prefers-color-scheme` and `prefers-reduced-motion`.
- **Test both** before calling a UI task done: browser device mode plus automated viewport tests (Playwright) when the frontend exists. State in the PR which viewports were checked.
- Grafana dashboards: check them in a narrow browser window too, and note limitations in the About page.

## 6. Stack summary
| Layer | Choice | ADR |
|---|---|---|
| Process | ADRs | [0001](docs/decisions/0001-record-architecture-decisions.md) (Accepted) |
| Runtime (dev) | Docker Compose, locally | [0002](docs/decisions/0002-build-locally-first-with-docker-compose.md) |
| First source | NOAA SWPC real-time solar wind (`json/rtsw/*`) | [0003](docs/decisions/0003-first-data-source-noaa-swpc-real-time-solar-wind.md) |
| Ingestion | Python + httpx + pydantic, APScheduler 3.x, raw landing zone | [0004](docs/decisions/0004-python-scheduled-pollers-with-raw-landing-zone.md) |
| Storage | PostgreSQL + TimescaleDB (+ PostGIS later) | [0005](docs/decisions/0005-postgresql-timescaledb-for-time-series-storage.md) |
| API | FastAPI | [0006](docs/decisions/0006-fastapi-for-backend-api.md) |
| UI | Grafana now, React + Plotly.js later | [0007](docs/decisions/0007-grafana-now-react-later-for-frontend.md) |
| Architecture | Modular monolith, a few containers | [0008](docs/decisions/0008-modular-monolith-before-microservices.md), [0014](docs/decisions/0014-when-to-use-more-than-one-docker-container.md) |
| Docs | About page for every section | [0009](docs/decisions/0009-about-this-page-for-every-section.md) |
| Version control | git + GitHub + Actions | [0010](docs/decisions/0010-use-git-and-github-from-day-one.md) |
| Cloud | Deferred; criteria defined | [0011](docs/decisions/0011-cloud-deployment-target-deferred-with-criteria.md) |
| Responsive UI | Mobile-first, defined breakpoints | [0012](docs/decisions/0012-responsive-design-mobile-and-desktop.md) |
| Design process | Study existing sites first | [0013](docs/decisions/0013-design-by-studying-existing-sites.md) |
| Rust | Only for measured hot paths (PyO3) | [0015](docs/decisions/0015-where-rust-could-fit.md) |
| Data science | Documented, reproducible workflow as a feature | [0016](docs/decisions/0016-data-science-workflow-as-first-class-feature.md) |
| AI agents | Small, read-only, evaluated agents; build with AGENTS.md | [0017](docs/decisions/0017-where-ai-agents-fit.md) |

All but 0001 are **Proposed**. Ask before building on a Proposed decision in a way that would be costly to undo.

## 7. Repo layout
```
.
├── AGENTS.md  CLAUDE.md  GROK.md  README.md
├── .cursor/rules/agents.mdc     # Cursor rule → points here
├── .env.example  .gitignore
├── docker-compose.yml           # (Phase 1) db, ingest, api, grafana
├── ingest/                      # Python pollers (one module per source)
├── api/                         # FastAPI service
├── db/migrations/               # numbered SQL migrations
├── dashboards/                  # Grafana provisioning (datasources + dashboard JSON)
├── web/                         # (Phase 3) React frontend
├── assets/brand/                # TI logo/graphics
├── data/raw/                    # raw landing zone (git-ignored)
└── docs/
    ├── decisions/               # ADRs + index/template (README.md)
    ├── about/                   # one About page per site page
    ├── research/                # data_sources.md, design_survey.md (forthcoming)
    ├── about-this-page-template.md
    ├── ROADMAP.md
    ├── ideas.md
    ├── data-science-workflow.md # how analysis/modelling is done here (follow it)
    ├── ai-agents.md             # agent use: building TI + agents in the product
    └── links.md                 # relevant articles, newest first
```

## 8. Conventions
**Git workflow**
- `main` is always working. Work on short-lived branches: `feat/…`, `fix/…`, `docs/…`, `adr/NNNN-…`.
- **Small PRs** with one purpose each, ideally under about 300 changed lines. The PR description says what, why, how it was tested, which viewports were checked (UI), and links ADR/About updates.
- Commit messages are imperative and specific ("Add SWPC wind poller with upsert on (time_tag, source)"). Conventional Commits prefixes (`feat:`, `fix:`, `docs:`) are welcome.
- Never force-push `main` and never rewrite shared history.

**Code and tests**
- Python 3.12+, formatted and linted with `ruff`, type hints everywhere, `pytest` tests for parsing, validation, and upsert logic. Network calls are mocked in unit tests.
- SQL changes only via new numbered files in `db/migrations/`; never edit an applied migration.
- Pollers are polite: timeouts, descriptive `User-Agent`, respect documented rate limits (CelesTrak: at most once per 2 h per group), and stop and log on 4xx rather than retry-hammering.
- CI (GitHub Actions) runs lint and tests on every PR.

**Secrets**
- **Never commit secrets.** Real values live in `.env` (git-ignored). Every variable must be listed with a dummy value and a comment in `.env.example`.
- If a secret is ever committed, treat it as leaked: rotate it, then clean history.

## 9. The repo lives in Dropbox: be careful
The working copy is at `~/Dropbox/TI/` on Howard's Mac. Dropbox syncs files one by one and doesn't understand git, so `.git/` can get corrupted (lock files, half-synced objects, "conflicted copy" files) and large folders like `node_modules/`, `.venv/`, and `data/` waste sync bandwidth.
- **GitHub is the real backup**: push often, and don't rely on Dropbox for history.
- Use the repo from **one machine at a time**.
- Have Dropbox ignore heavy or generated folders. On macOS: `xattr -w com.dropbox.ignored 1 <folder>` (see [Dropbox: ignored files](https://help.dropbox.com/sync/ignored-files)). Good candidates are `node_modules`, `.venv`, `data`, and Docker volumes.
- Database data must live in **Docker named volumes**, not bind mounts inside Dropbox.
- A safer long-term setup is to keep the clone outside Dropbox (e.g., `~/code/tachocline`). See [ADR 0010](docs/decisions/0010-use-git-and-github-from-day-one.md).

## 10. Data science and AI agent work
- Analysis and modelling follow [docs/data-science-workflow.md](docs/data-science-workflow.md): reusable code goes in a tested `analysis/` package (not notebooks), raw data is immutable, validation is time-aware, and predictions are published with uncertainty ([ADR 0016](docs/decisions/0016-data-science-workflow-as-first-class-feature.md)).
- Any in-product AI agent follows [docs/ai-agents.md](docs/ai-agents.md) and [ADR 0017](docs/decisions/0017-where-ai-agents-fit.md): read-only tools through the API, grounded and cited answers, an eval set before shipping, cost caps, and AI output labelled.
- As a coding agent, verify citations by resolving IDs (DOI/arXiv/ADS) and checking titles match. A wrong arXiv citation was already caught once in this repo.

## 11. Data and science integrity
- Cite every data source on the page that uses it and in its About page.
- Label provisional or real-time data as such, and never present a model prediction as an observation.
- Science claims must link to a source (paper, agency page). Mark speculation as speculation.
