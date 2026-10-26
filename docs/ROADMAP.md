# Roadmap

Phased milestones. Each phase ends with something demoable, its About pages written, and its ADRs reviewed. Howard's original comments are numbered **[H1]–[H11]** (see [ideas.md](ideas.md#howards-comments-2026-10-20) for the full list).

## Phase 0: Foundations *(now)*
- [x] Create the GitHub repo `tachocline`, push this tree, protect `main` **[H1]**, [ADR 0010](decisions/0010-use-git-and-github-from-day-one.md). `GET` of `main` shows it protected, with `lint` and `test` required from GitHub Actions (app id 15368) and `enforcement_level` `everyone`. See [github-workflow.md](github-workflow.md).
- [ ] Decide public vs private; enable secret scanning
- [ ] Review Proposed ADRs 0002–0018
- [ ] Seed GitHub Issues/Milestones/Project from this roadmap and finish Project views in the web UI, [ADR 0018](decisions/0018-plan-work-with-github-issues-milestones-projects.md) and accept or revise them
- [ ] Handle Dropbox + git: one machine, ignore heavy folders, or clone outside Dropbox (AGENTS.md §9)
- [ ] Add the TI solar graphic to `assets/brand/` when ready **[H3]**

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
- [ ] CelesTrak GP data for a **chosen set of satellites tracked over time**. The starter set is ISS, Landsat 8, Landsat 9, HST, and Swift ([tracked-satellites.md](research/tracked-satellites.md), issue #33). Store that history with altitude derived from mean motion **[H6] [H11]**
- [ ] Join space weather ↔ satellite altitude-decay rate on a dashboard
- [ ] FastAPI read-only endpoints, [ADR 0006](decisions/0006-fastapi-for-backend-api.md)

## Phase 3: Public website
- [ ] `docs/research/design_survey.md`: 5 design-renowned + 5 scientific sites, mobile and desktop **[H4]**, [ADR 0013](decisions/0013-design-by-studying-existing-sites.md)
- [ ] Design brief using the TI graphic **[H3]**
- [ ] React + Plotly.js frontend reading only from the API, [ADR 0007](decisions/0007-grafana-now-react-later-for-frontend.md)
- [ ] Mobile-first breakpoints and Playwright viewport tests for every page **[H5]**, [ADR 0012](decisions/0012-responsive-design-mobile-and-desktop.md)
- [ ] About link on every page, [ADR 0009](decisions/0009-about-this-page-for-every-section.md)
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
