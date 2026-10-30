# Roadmap

Phased milestones. Each phase ends with something demoable, its About pages written, and its ADRs reviewed. Howard's original comments are numbered **[H1]–[H11]** (see [ideas.md](ideas.md#howards-comments-2026-10-20) for the full list).

## Phase 0: Foundations *(now)*
- [x] Create the GitHub repo `tachocline`, push this tree, protect `main` **[H1]**, [ADR 0010](decisions/0010-use-git-and-github-from-day-one.md). `GET` of `main` shows it protected, with `lint` and `test` required from GitHub Actions (app id 15368) and `enforcement_level` `everyone`. See [github-workflow.md](github-workflow.md).
- [ ] Decide public vs private; enable secret scanning
- [x] Review ADRs 0001–0023 (all Accepted; 0005 Status was normalized from "Approved")
- [ ] Seed GitHub Issues/Milestones/Project from this roadmap and finish Project views in the web UI, [ADR 0018](decisions/0018-plan-work-with-github-issues-milestones-projects.md) and accept or revise them
- [ ] Handle Dropbox + git: one machine, ignore heavy folders, or clone outside Dropbox (AGENTS.md §9)
- [x] Add the TI solar graphic to `assets/brand/` (issue #22): SVG master, icons, heroes, `LICENSE-ASSETS.md` **[H3]**

## Phase 1: First feed end to end (solar wind)
- [x] `docker-compose.yml`: `db` (TimescaleDB), `migrate`, `ingest`, `grafana`, [ADR 0002](decisions/0002-build-locally-first-with-docker-compose.md), [0014](decisions/0014-when-to-use-more-than-one-docker-container.md) **[H10]**
- [x] First migration: `solar_wind` and `rtsw_mag_1m` hypertables, `ingest_log`, read-only role (issue #25), [ADR 0005](decisions/0005-postgresql-timescaledb-for-time-series-storage.md)
- [x] SWPC `rtsw_wind_1m` + `rtsw_mag_1m`: raw landing zone (issue #26) → validate, upsert, `ingest_log` (issue #27), [ADR 0003](decisions/0003-first-data-source-noaa-swpc-real-time-solar-wind.md), [0004](decisions/0004-python-scheduled-pollers-with-raw-landing-zone.md)
- [ ] Grafana dashboard: speed, density, Bz, plus pipeline health **[H5]** (issue #28). JSON is provisioned; the narrow-window limit is written on the dashboard (full-width stacked panels; Grafana's own menu is unchanged below 640 px). A live browser check is still open.
- [x] GitHub Actions: ruff + pytest (`.github/workflows/ci.yml`)
- [x] About page: [`docs/about/solar-wind.md`](about/solar-wind.md) (issue #30), linked from the Grafana dashboard. A live narrow-window browser check of that dashboard is still open (issue #28).

## Phase 2: Space-weather context + satellites
- [x] GOES X-ray flux (flares): poller, `goes_xray_flux` hypertable, log-scale panel on the Solar wind dashboard (issue #31)
- [x] Kp and SWPC alerts: 1-minute and 3-hour Kp plus alerts.json, Bz/Kp panel on the Solar wind dashboard (issue #32)
- [x] CelesTrak GP data for a **chosen set of satellites tracked over time**. The starter set is ISS, Landsat 8, Landsat 9, HST, and Swift ([tracked-satellites.md](research/tracked-satellites.md), issue #33). History and a two-body altitude from mean motion are stored by the 2-hour poller (issue #34, [About page](about/satellite-gp.md)). Issue #33 stays open until a tracked object has a decay date. **[H6] [H11]**
- [x] Join space weather ↔ satellite altitude-decay rate on a dashboard. Perigee, kilometers per day, and 3-hour Kp with storm bands are the **Orbit decay** dashboard (issue #35, [About page](about/orbit-decay.md)). A rate appears after a satellite has two epochs.
- [x] GFZ definitive 3-hour Kp since 1932 in `gfz_kp_3h`, separate from the SWPC estimate, `GET /api/kp-gfz` ([ADR 0022](decisions/0022-store-gfz-kp-apart-from-swpc-estimates.md))
- [x] Space-Track `gp_history` for the starter set when credentials are set, and `GET /api/satellite-decay` for kilometers per day ([ADR 0023](decisions/0023-backfill-gp-history-and-serve-perigee-rate.md))
- [x] FastAPI read-only endpoints: `/api/health`, `/api/solar-wind`, `/api/mag`, `/api/goes-xray`, `/api/kp-1m`, `/api/kp-3h`, `/api/alerts`, `/api/satellite-perigee`, `/api/sources`, `/api/ingest-log`, OpenAPI at `/docs` (issue #36, [ADR 0006](decisions/0006-fastapi-for-backend-api.md), [About page](about/api.md)).

## Phase 3: Public website
- [x] Design survey: SpaceX-style brief plus space and science references ([design_survey.md](research/design_survey.md), issue #37), [ADR 0013](decisions/0013-design-by-studying-existing-sites.md)
- [x] Design brief using the TI graphic **[H3]** (issue #38): [`docs/design-brief.md`](design-brief.md), accent choice in [ADR 0025](decisions/0025-brand-accent-from-logo-orange.md)
- [x] First public page: radial Kp plots (day, month, year; 11-year plot deferred until a Kp backfill), [ADR 0020](decisions/0020-radial-time-plots-for-space-weather.md), [ADR 0021](decisions/0021-react-vite-page-with-svg-radial-plots.md)
- [ ] Rest of the React site (satellite, data, and workflow pages). Plotly.js waits for a later line-chart view, [ADR 0007](decisions/0007-grafana-now-react-later-for-frontend.md)
- [x] Mobile-first breakpoints and Playwright viewport tests for every page **[H5]** (issue #40). Space-weather checks 320 (no horizontal scroll), 375, 768, and 1280 px in CI. [ADR 0012](decisions/0012-responsive-design-mobile-and-desktop.md)
- [x] About link on every page (issue #41). `docs/about/*.md` is rendered in the React site; the space-weather page links to `/about/space-weather`. [ADR 0009](decisions/0009-about-this-page-for-every-section.md), [ADR 0024](decisions/0024-render-about-markdown-in-react.md)
- [ ] **"How the science is done" page** built from [data-science-workflow.md](data-science-workflow.md), with its own About page, [ADR 0016](decisions/0016-data-science-workflow-as-first-class-feature.md)
- [ ] **First AI agent: space-weather briefing** (SWPC alerts + current indices → short cited briefing, labelled AI-generated, eval set in CI), [ADR 0017](decisions/0017-where-ai-agents-fit.md), [ai-agents.md](ai-agents.md)
- [ ] TI **MCP server** wrapping the read-only API (may slip to Phase 4)

## Phase 4: Deploy to the cloud
- [ ] New ADR choosing the provider using the criteria in [ADR 0011](decisions/0011-cloud-deployment-target-deferred-with-criteria.md) (AWS / Google Cloud / other) **[H2]**
- [ ] Infrastructure as code, billing alerts, CI/CD deploy, uptime monitoring
- [ ] Natural-language (text-to-SQL) query agent with SELECT-only role, timeouts, row limits, and the SQL shown to the user ([ai-agents.md](ai-agents.md))

## Phase 5: Value-add science features
- [ ] **Drag Watch, the orbital decay and re-entry predictor**, run through the full [data science workflow](data-science-workflow.md) (provenance → backtests vs SATCAT decay dates → intervals → monitoring), [ADR 0016](decisions/0016-data-science-workflow-as-first-class-feature.md): how long tracked satellites stay up, and how flares/storms inflate the thermosphere and speed up drag; Starlink Feb 2022 as the validation case study **[H6] [H11]**
- [ ] **Rust (PyO3) propagation/drag module** benchmarked against Python, [ADR 0015](decisions/0015-where-rust-could-fit.md) **[H9]**
- [ ] **Sun-as-a-star:** compare solar activity with stellar activity (S-index, Ca II H&K) from Howard's domain **[H7]**
- [ ] **Space weather → power grids:** "impact of flare/storm X on power grids" explainer **[H8]**

- [ ] Stretch: ingestion anomaly-triage agent; ADS/arXiv literature agent ([ai-agents.md](ai-agents.md))
- [ ] Experiment tracking (MLflow) once model variants multiply (new ADR)

Order within Phase 5 is flexible; each item needs its own ADR(s) and About page.
