#!/usr/bin/env python3
"""Generates issues.json (the GitHub plan) from a compact description of docs/ROADMAP.md.
Edit this file, re-run `python3 build_plan.py`, then re-run setup_labels_milestones_issues.sh
(it only creates what's missing)."""
import json, re, glob, os

REPO_URL = "https://github.com/howardisaacson/tachocline-industries/blob/main/"
# Path to your local clone (set TI_REPO=/path/to/tachocline-industries when running on the Mac)
DOCS = os.path.join(os.environ.get("TI_REPO", "/workspace/tachocline/repo"), "docs", "decisions")

def L(path, text=None):
    # Issue bodies are not rendered relative to the repo tree, so "relative" links
    # are written as repo-absolute blob URLs (work for the private repo when logged in).
    return f"[{text or path}]({REPO_URL}{path})"

labels = [
  # type
  ("type: feature","1D76DB","New user-visible capability"),
  ("type: docs","0075CA","Documentation, About pages, explanations"),
  ("type: research","5319E7","Investigation or survey before building"),
  ("type: adr","D4C5F9","Write or review an Architecture Decision Record"),
  ("type: chore","C5DEF5","Setup, maintenance, tooling, CI"),
  ("type: bug","D73A4A","Something isn't working"),
  # area
  ("area: ingest","FBCA04","Pollers, raw landing zone, validation"),
  ("area: db","F9D0C4","PostgreSQL / TimescaleDB, migrations"),
  ("area: api","0E8A16","FastAPI backend"),
  ("area: dashboards","FEF2C0","Grafana dashboards"),
  ("area: web","C2E0C6","React frontend, design, responsive UI"),
  ("area: ds","BFD4F2","Data science: features, models, backtests"),
  ("area: agents","E99695","AI agents, MCP, evals"),
  ("area: infra","BFDADC","Docker, CI/CD, cloud, GitHub settings"),
  ("area: rust","B60205","Rust / PyO3 work"),
  ("area: brand","FF9F1C","Logo, graphics, visual identity"),
  # meta
  ("good first issue","7057FF","Small, well-defined starter task"),
  ("learning","006B75","Main goal is learning a new skill (note it for interviews)"),
]

milestones = [
  ("Phase 0: Foundations","GitHub repo hygiene, ADR review, Dropbox/git safety, brand graphic. See docs/ROADMAP.md."),
  ("Phase 1: First feed end to end","NOAA SWPC solar wind: poll -> raw landing zone -> TimescaleDB -> Grafana, with CI and an About page."),
  ("Phase 2: Space weather + satellites","GOES X-rays, Kp, alerts; CelesTrak satellite history with altitude; FastAPI read endpoints."),
  ("Phase 3: Public website","Design survey and brief, React + Plotly frontend, responsive tests, About links, science page, first AI agent."),
  ("Phase 4: Deploy to the cloud","Choose provider (ADR 0011 criteria), infrastructure as code, deploy pipeline, text-to-SQL agent."),
  ("Phase 5: Value-add science","Drag Watch, Rust benchmark, Sun-as-a-star, power-grid explainer, stretch agents, MLflow."),
]
M = [m[0] for m in milestones]

issues = []
def add(key, title, ms, labs, why, ac, related, learn, parent=None):
    body = "## Why\n" + why + "\n\n## Acceptance criteria\n" + "\n".join(f"- [ ] {a}" for a in ac)
    body += "\n\n## Related docs / ADRs\n" + "\n".join(f"- {r}" for r in related)
    body += "\n\n## What you'll learn\n" + learn + "\n\n_Generated from docs/ROADMAP.md by gh-setup/build_plan.py._"
    d = {"key": key, "title": title, "milestone": M[ms], "labels": labs, "body": body}
    if parent: d["parent"] = parent
    issues.append(d)

RM = L("docs/ROADMAP.md","ROADMAP")
def adr(n):
    f = glob.glob(f"{DOCS}/{n:04d}-*.md")[0]
    return L("docs/decisions/" + os.path.basename(f), f"ADR {n:04d}")

# ---------- Phase 0 ----------
add("p0-protect","Protect main and enable secret scanning",0,["type: chore","area: infra","learning"],
  "The repo exists (private). `main` should only change through PRs that pass CI, and leaked secrets should be blocked on push.",
  ["Branch protection (or a ruleset) on `main`: require PR, require status checks once CI exists","Secret scanning + push protection enabled (check availability for private repos on your plan)","Note what you enabled in docs/github-workflow.md"],
  [adr(10), L("docs/github-workflow.md")], "Branch protection vs rulesets, secret scanning, why solo devs still use PRs.")
add("p0-visibility","Decide repo visibility: private now, public when?",0,["type: chore","area: infra"],
  "ADR 0010 recommends public for portfolio value; the repo is currently private.",
  ["Decide and record the trigger for going public (e.g., end of Phase 1)","Check history for anything that must not be public before flipping"],
  [adr(10)], "Trade-offs of building in public; auditing git history.")
add("p0-adr-epic","Review all Proposed ADRs (0002–0018)",0,["type: adr","learning"],
  "Every decision so far is Proposed. Reviewing each one is the fastest way to understand (and be able to defend) the architecture.",
  ["Every sub-issue closed (Accepted, revised, or Rejected)","ADR index statuses match"],
  [L("docs/decisions/README.md","ADR index")], "How ADR lifecycles work; how parent issues and sub-issues track a group of work.")
titles = {}
for f in sorted(glob.glob(f"{DOCS}/0*.md")):
    n = int(os.path.basename(f)[:4])
    t = re.search(r"^# \d+\. (.+)$", open(f).read(), re.M).group(1)
    titles[n] = t
titles.setdefault(18, "Plan work with GitHub Issues, Milestones, and Projects")
for n in range(2, 19):
    path = glob.glob(f"{DOCS}/{n:04d}-*.md")
    rel = L("docs/decisions/" + os.path.basename(path[0]), f"ADR {n:04d}") if path else f"ADR {n:04d}"
    add(f"adr-{n:04d}", f"Review ADR {n:04d}: {titles[n]}", 0, ["type: adr"],
      f"ADR {n:04d} is Proposed. Read it, challenge the options, then accept, revise, or reject it.",
      ["Read the ADR and its Learn more links","Can explain the decision out loud in 2–3 sentences (its interview section)",
       "Status changed to Accepted / Rejected (or revised via PR) and index updated","Close this issue from the PR (`Closes #<this>`)"],
      [rel, L("docs/decisions/README.md","ADR index")], "The reasoning behind this part of the stack, well enough to defend it in an interview.",
      parent="p0-adr-epic")
add("p0-dropbox","Make the Dropbox + git setup safe",0,["type: chore","area: infra","learning","good first issue"],
  "The working copy lives in Dropbox, which can corrupt `.git/` and wastes sync on heavy folders.",
  ["Decide: keep in Dropbox (one machine, ignored folders) or move the clone to ~/code","Mark node_modules/.venv/data as Dropbox-ignored if staying","Docker DB data uses named volumes, not Dropbox paths"],
  [L("AGENTS.md","AGENTS.md §9"), adr(10)], "How file sync differs from version control.")
add("p0-brand","Add the TI solar graphic to assets/brand",0,["type: feature","area: brand"],
  "The site needs its identity (eclipse, prominences, plage, faculae, sunspots, flares, sub-surface loops, satellites).",
  ["Vector master + web icons + wide/tall hero added per assets/brand/README.md","LICENSE-ASSETS.md records creator and rights"],
  [L("assets/brand/README.md"), RM], "Asset pipelines: SVG masters, responsive images, licensing.")

# ---------- Phase 1 ----------
add("p1-epic","Phase 1: solar wind end to end (poll → store → chart)",1,["type: feature","area: ingest"],
  "The first milestone proves the whole pipeline with one feed.",
  ["All sub-issues closed","`docker compose up` shows live solar wind in Grafana","README quick start works on a fresh clone"],
  [adr(3), adr(4), RM], "How the pieces of a data platform connect end to end.")
add("p1-compose","docker-compose.yml with db, migrate, ingest, grafana",1,["type: chore","area: infra","learning"],
  "One command should start the whole local stack.",
  ["Services: db (timescale/timescaledb), migrate (one-shot), ingest, grafana","DB uses a named volume and a healthcheck; others wait via depends_on","All config from .env (see .env.example)"],
  [adr(2), adr(14)], "Compose services, volumes, networks, healthchecks, startup order.", parent="p1-epic")
add("p1-schema","First migration: solar wind, magnetic field, ingest_log tables",1,["type: feature","area: db","learning","good first issue"],
  "Tables need natural keys so re-ingesting is idempotent.",
  ["db/migrations/0001_*.sql creates hypertables keyed on (time_tag, source)","ingest_log table for run health","Read-only role for Grafana/API"],
  [adr(5)], "Primary keys, hypertables, roles and GRANTs.", parent="p1-epic")
add("p1-poller","SWPC poller: fetch rtsw_wind_1m + rtsw_mag_1m into the raw landing zone",1,["type: feature","area: ingest","learning"],
  "SWPC only serves ~24 h, so we must fetch on a schedule and keep our own history.",
  ["APScheduler job every 5 min with timeout + User-Agent","Raw response saved to data/raw/swpc_rtsw/<date>/","Stops and logs on 4xx; unit tests with mocked HTTP"],
  [adr(3), adr(4)], "Scheduling, HTTP clients, polite polling, raw zones.", parent="p1-epic")
add("p1-upsert","Validate with pydantic and upsert into TimescaleDB",1,["type: feature","area: ingest","area: db"],
  "Validation catches upstream schema changes; upserts make reruns safe.",
  ["pydantic models for wind and mag rows; rejects counted","INSERT … ON CONFLICT DO UPDATE on (time_tag, source)","ingest_log row per run; tests prove a rerun adds no duplicates"],
  [adr(4), adr(5)], "Idempotency, schema validation, transactional writes.", parent="p1-epic")
add("p1-grafana","Grafana dashboard: solar wind + pipeline health",1,["type: feature","area: dashboards","learning"],
  "First visible result, plus a way to see if ingestion is healthy.",
  ["Provisioned datasource + dashboard JSON in dashboards/","Panels: speed, density, Bz (active source), minutes since last good ingest","Checked in a narrow (mobile-width) window; limits noted"],
  [adr(7), adr(12)], "Grafana provisioning, time-series SQL with time_bucket().", parent="p1-epic")
add("p1-ci","GitHub Actions CI: ruff + pytest on every PR",1,["type: chore","area: infra","good first issue","learning"],
  "Automated checks make PRs trustworthy and enable branch protection checks.",
  [".github/workflows/ci.yml runs ruff and pytest","Required status check on main"],
  [adr(10), L("docs/github-workflow.md")], "CI workflows, required checks.", parent="p1-epic")
add("p1-about","About page: docs/about/solar-wind.md",1,["type: docs"],
  "Every page ships with an About page (ADR 0009).",
  ["Written from the template, including Mermaid data flow and interview talking points","Linked from the Grafana dashboard"],
  [adr(9), L("docs/about-this-page-template.md")], "Explaining a system clearly, which is an interview skill in itself.", parent="p1-epic")

# ---------- Phase 2 ----------
add("p2-goes","Ingest GOES X-ray flux (flares)",2,["type: feature","area: ingest"],
  "Flares are the most visible solar events; same server and pattern as Phase 1.",
  ["Poller + table + Grafana panel (log scale, flare-class bands)","About page updated"],
  [L("docs/research/data_sources.md","data_sources.md")], "Reusing a pipeline pattern for a second source.")
add("p2-kp","Ingest Kp index and SWPC alerts",2,["type: feature","area: ingest"],
  "Kp is the geomagnetic response; alerts feed the future briefing agent.",
  ["Kp (1-min estimated + 3-hourly) and alerts.json stored","Dashboard correlates Bz with Kp"],
  [L("docs/research/data_sources.md","data_sources.md")], "Joining cause and effect time series.")
add("p2-satset","Choose the tracked satellite set",2,["type: research","area: ds","good first issue"],
  "Drag Watch needs a defined set (ISS, Hubble, Tiangong, Starlink incl. Feb 2022 group, a decayed cubesat).",
  ["List of NORAD IDs with reasons, in docs/research/","Ground-truth decay dates identified for decayed objects"],
  [L("docs/research/satellite_orbit_decay_data.md","orbit decay research")], "Sampling design for a modelling dataset.")
add("p2-celestrak","Store GP/TLE history for tracked satellites with derived altitude",2,["type: feature","area: ingest","area: ds"],
  "Altitude over time is the core Drag Watch dataset.",
  ["Polls at most once per 2 h (CelesTrak policy); Space-Track gp_history backfill optional","Perigee/apogee altitude computed and tested against known values"],
  [L("docs/research/satellite_orbit_decay_data.md","orbit decay research")], "Orbital elements, rate-limit etiquette, derived columns.")
add("p2-decaydash","Dashboard: space weather vs satellite altitude decay",2,["type: feature","area: dashboards","area: ds"],
  "First visual evidence that storms speed up decay.",
  ["Altitude and dh/dt per satellite with storm periods shaded","About page"],
  [adr(16)], "Exploratory visualisation for a hypothesis.")
add("p2-api","FastAPI read-only endpoints",2,["type: feature","area: api","learning"],
  "The public site and agents must go through an API, not the database.",
  ["/api/health, /api/solar-wind, /api/sources, /api/ingest-log with limits","OpenAPI docs at /docs; tests with TestClient","api service in Compose"],
  [adr(6)], "REST design, pydantic response models, OpenAPI.")

# ---------- Phase 3 ----------
add("p3-survey","Finalize the design survey (5 design + 5 scientific sites)",3,["type: research","area: web"],
  "A draft exists; finalize the site list and mobile/desktop scoring.",
  ["Final 10 sites chosen with Howard","Unverified claims checked or removed","Patterns to adopt / avoid summarised"],
  [L("docs/research/design_survey.md","design_survey.md"), adr(13)], "Competitive analysis as a design method.")
add("p3-brief","Design brief using the TI graphic",3,["type: docs","area: web","area: brand"],
  "Turn the survey into palette, type scale, grid, chart style, components.",
  ["docs/design-brief.md","Significant choices become ADRs"],
  [adr(13), adr(12)], "Design systems vocabulary.")
add("p3-react","Scaffold the React + Plotly.js frontend reading from the API",3,["type: feature","area: web","learning"],
  "The public portfolio site.",
  ["ADR for build tool/hosting written first","First page (solar wind) renders from /api","web service or static build in Compose"],
  [adr(7)], "React components, state, fetching data, build tooling.")
add("p3-playwright","Responsive breakpoints + Playwright viewport tests",3,["type: chore","area: web","learning"],
  "Every page must work on mobile and desktop (ADR 0012).",
  ["Tests at 375, 768, 1280 px in CI","No horizontal scroll at 320 px"],
  [adr(12)], "Responsive CSS and end-to-end testing.")
add("p3-aboutlinks","About link on every site page",3,["type: docs","area: web"],
  "ADR 0009: each page explains itself.",
  ["About markdown rendered in the React site","Every page has an About link"],
  [adr(9)], "Docs-as-code rendered in an app.")
add("p3-science","Build the 'How the science is done' page",3,["type: feature","area: web","area: ds","type: docs"],
  "Showcases the data science workflow (ADR 0016).",
  ["Page built from data-science-workflow.md incl. Mermaid diagram","Own About page; mobile + desktop checked"],
  [adr(16), L("docs/data-science-workflow.md")], "Communicating process, not just results.")
add("p3-briefing","First AI agent: space-weather briefing",3,["type: feature","area: agents","learning"],
  "Small, read-only, evaluable agent (ADR 0017).",
  ["Fetches via the TI API only; each sentence cites a product/time","Labelled AI-generated; cached per new alert; spend cap","Eval set of past alerts runs in CI; model ADR written"],
  [adr(17), L("docs/ai-agents.md")], "Tool calling, grounding, evals, cost control.")
add("p3-mcp","TI MCP server wrapping the read-only API",3,["type: feature","area: agents","area: api"],
  "Lets AI clients query live TI data safely (may slip to Phase 4).",
  ["Tools: get_solar_wind, get_alerts, get_satellite_altitude","Uses API, never DB credentials; documented in an About page"],
  [adr(17), L("docs/ai-agents.md")], "Model Context Protocol servers.")

# ---------- Phase 4 ----------
add("p4-cloudadr","ADR: choose the cloud provider",4,["type: adr","area: infra","learning"],
  "ADR 0011 deferred the choice and defined the criteria.",
  ["Job-posting count for target roles","Scored comparison (AWS / Google Cloud / other) against ADR 0011 criteria","New ADR Proposed"],
  [adr(11)], "Evaluating cloud platforms against explicit criteria.")
add("p4-deploy","Infrastructure as code, billing alerts, CI/CD deploy, uptime monitoring",4,["type: chore","area: infra","learning"],
  "Make the site public and keep it running cheaply.",
  ["Terraform/OpenTofu (or chosen tool) in repo","Billing alerts set before anything runs","Deploy on merge to main; uptime check"],
  [adr(11)], "IaC, CD pipelines, cost control.")
add("p4-text2sql","Text-to-SQL query agent with guardrails",4,["type: feature","area: agents","area: db"],
  "Natural-language questions over TI data.",
  ["SELECT-only role on curated views; statement_timeout; row limits","Only single SELECTs accepted; SQL shown to the user; queries logged","Eval set of ~30 questions"],
  [adr(17), L("docs/ai-agents.md")], "LLM safety engineering, DB permissions.")

# ---------- Phase 5 ----------
add("p5-dw-epic","Drag Watch: storm-driven orbital decay and re-entry predictor",5,["type: feature","area: ds"],
  "The flagship science feature, run through the full data science workflow; Starlink Feb 2022 as validation case.",
  ["All sub-issues closed","Public page with predictions as ranges and backtest errors"],
  [adr(16), L("docs/data-science-workflow.md"), L("docs/research/satellite_orbit_decay_data.md","orbit decay research")],
  "End-to-end applied data science on a physical problem.")
add("p5-dw-data","Drag Watch: data acquisition and provenance",5,["type: feature","area: ds","area: ingest"],
  "Every number must trace back to its source bytes.",
  ["GP history, SATCAT decay dates, GFZ Kp/ap/F10.7 file in raw zone with manifest (URL, time, sha256)"],
  [adr(16)], "Data provenance and manifests.", parent="p5-dw-epic")
add("p5-dw-features","Drag Watch: EDA and feature engineering",5,["type: feature","area: ds","learning"],
  "Encode the physics: altitude, lagged Ap/Kp, F10.7 (81-day), MSIS density.",
  ["Notebook EDA; reusable features in analysis/ with tests","ISS reboosts detected"],
  [adr(16)], "Physics-informed features, notebooks vs packages.", parent="p5-dw-epic")
add("p5-dw-model","Drag Watch: baselines and physics-lite decay model",5,["type: feature","area: ds"],
  "Every model must beat persistence and a simple drag model.",
  ["Persistence baseline","dh/dt ≈ −k·ρ(h, F10.7, Ap) fit per satellite; scenario integration"],
  [adr(16)], "Baselines and model selection.", parent="p5-dw-epic")
add("p5-dw-backtest","Drag Watch: backtest against real decay dates (incl. Starlink Feb 2022)",5,["type: feature","area: ds"],
  "Honest validation against ground truth.",
  ["Time-ordered backtests at T−30/7/1 days vs SATCAT decay dates","Error by altitude band and activity level published"],
  [adr(16)], "Time-aware validation, leakage avoidance.", parent="p5-dw-epic")
add("p5-dw-page","Drag Watch: uncertainty, public page, and About",5,["type: feature","area: ds","area: web"],
  "Predictions are ranges; the page explains method and limits.",
  ["Intervals from backtest residuals + quiet/storm scenarios","Page + About; mobile + desktop checked"],
  [adr(16), adr(9), adr(12)], "Communicating uncertainty.", parent="p5-dw-epic")
add("p5-rust","Rust (PyO3) propagation/drag module with benchmark",5,["type: feature","area: rust","learning"],
  "Learn when Rust is worth it, driven by profiling (ADR 0015).",
  ["Python baseline profiled first","PyO3/maturin crate; numerical agreement tests","Benchmark vs NumPy and C++-backed sgp4 published, even if Rust doesn't win"],
  [adr(15)], "Rust, PyO3, profiling, benchmarking.")
add("p5-sunstar","Sun-as-a-star: research public stellar activity datasets",5,["type: research","area: ds"],
  "Compare solar activity with Sun-like stars (S-index, Ca II H&K), drawing on Howard's domain.",
  ["Citable public datasets identified (with licences)","Feature sketch + ADR if significant"],
  [L("docs/ideas.md","ideas.md")], "Bringing domain expertise into a product.")
add("p5-grid","Space weather and power grids explainer",5,["type: feature","type: docs"],
  "Educational chain: flare → CME → Kp/G-level → typical grid impacts (not damage predictions).",
  ["Uses NOAA G-scale descriptions; historic examples verified before use","About page"],
  [L("docs/ideas.md","ideas.md")], "Science communication with careful framing.")
add("p5-agents","Stretch agents: ingestion anomaly triage and ADS/arXiv literature",5,["type: feature","area: agents"],
  "Further agents once the first is proven.",
  ["Triage agent drafts issues but never auto-fixes","Literature agent resolves every ID via ADS/arXiv and checks titles"],
  [adr(17), L("docs/ai-agents.md")], "Agent evaluation and citation integrity.")
add("p5-mlflow","ADR: experiment tracking with MLflow",5,["type: adr","area: ds"],
  "Adopt when model variants multiply (ADR 0016).",
  ["ADR comparing simple log / MLflow / DVC experiments","Self-hosted MLflow container if accepted"],
  [adr(16)], "Experiment tracking and model registries.")

plan = {"repo": "howardisaacson/tachocline-industries",
        "labels": [{"name": n, "color": c, "description": d} for n, c, d in labels],
        "milestones": [{"title": t, "description": d} for t, d in milestones],
        "issues": issues}
keys = [i["key"] for i in issues]; assert len(keys) == len(set(keys))
titles_ = [i["title"] for i in issues]; assert len(titles_) == len(set(titles_))
names = {l["name"] for l in plan["labels"]}
for i in issues:
    assert set(i["labels"]) <= names, i
    assert i.get("parent") in (None, *keys)
json.dump(plan, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "issues.json"), "w"), indent=2, ensure_ascii=False)
print(len(labels), "labels,", len(milestones), "milestones,", len(issues), "issues,", sum(1 for i in issues if "parent" in i), "sub-issues")
