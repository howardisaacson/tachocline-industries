# 0007. Grafana now, React later for the frontend

- **Status:** Proposed
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
We need to *see* the data: live charts for the first milestone, and eventually a polished public portfolio site with pages, explanations, and "About this page" links ([ADR 0009](0009-about-this-page-for-every-section.md)). I'm still learning JavaScript and React. If the first chart waits until I've learned a frontend framework, the data pipeline sits unseen for weeks.

Key terms:
- **Dashboard tool:** an app where you build charts by writing queries, not code (e.g., Grafana).
- **Frontend:** the code that runs in the visitor's browser.
- **React:** a JavaScript library for building user interfaces out of reusable *components*.

## Options considered
### A. Grafana
- Pros: connects straight to PostgreSQL/TimescaleDB; live-updating time-series panels in minutes; alerting built in; dashboards can be saved as JSON in git ("provisioning"); widely used in industry for monitoring.
- Cons: looks like an ops tool, not a custom website; limited control over layout and narrative text; public sharing needs care.
### B. Streamlit or Plotly Dash (Python)
- Pros: pure Python; quick for data apps.
- Cons: sits between the two goals: less polished than React, less operational than Grafana; teaches neither frontend skills nor industry-standard monitoring.
### C. React + a charting library (e.g., Plotly.js) calling our API
- Pros: full control of design and storytelling; the most in-demand frontend skill; shows end-to-end SWE ability (browser → API → database).
- Cons: biggest learning curve (JavaScript, components, state, build tooling); slowest route to a first chart.
### D. Both, staged
- Pros: fast feedback now and a polished site later; the two serve different audiences.
- Cons: two things to maintain; some charts exist twice.

## Decision
We will stage it (option D):
1. **Now:** **Grafana** as a Compose service, reading TimescaleDB through a **read-only** database user, with dashboards provisioned from JSON files in `dashboards/`. It is the internal "mission control" for data and pipeline health (`ingest_log`).
2. **Later:** a **React** single-page site with Plotly.js charts that reads **only from the FastAPI service** ([ADR 0006](0006-fastapi-for-backend-api.md)). This is the public portfolio, with narrative pages and About sections.

Grafana stays as the internal monitoring view even after React exists.

## Consequences
- Easier: a visible result in the first milestone; learn SQL-driven charting first, then JavaScript with real data already flowing.
- Harder: two visualisation layers to keep consistent. Moving to React will need its own ADR (build tool, hosting, routing).
- Security: Grafana must not be exposed publicly with default credentials; use the read-only DB role.

## How to explain this in an interview
"I split visualisation by audience. Grafana is my internal mission control, reading TimescaleDB directly and watching pipeline health. The public site is React, which only talks to my FastAPI layer, never the database. Starting with Grafana meant I had live charts on day one while I learned React properly."

## Learn more
- Grafana docs, [PostgreSQL data source](https://grafana.com/docs/grafana/latest/datasources/postgres/) and [Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- React docs, [Learn React](https://react.dev/learn) and [Thinking in React](https://react.dev/learn/thinking-in-react)
- [Plotly JavaScript graphing library](https://plotly.com/javascript/)
