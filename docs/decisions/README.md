# Architecture Decision Records (ADRs)

## What is an ADR?
An **Architecture Decision Record** is a short markdown file that captures **one** important technical decision: what was decided, why, which alternatives were considered, and what the consequences are. The format was popularised by Michael Nygard in his 2011 post [*Documenting Architecture Decisions*](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

ADRs live in the repo next to the code (`docs/decisions/`), are numbered in order, and are **never deleted**. When a decision changes, a new ADR *supersedes* the old one, so the history stays readable.

## Why teams use them
- **Memory:** six months later, nobody remembers why we chose TimescaleDB over InfluxDB. The ADR does.
- **Onboarding:** new engineers read the ADRs and understand the system's shape in an hour.
- **Better decisions:** writing down the alternatives and trade-offs forces you to actually think about them.
- **Reviewable:** ADRs go through pull requests like code, so decisions get discussed in the open.
- **For this project:** each ADR is also interview prep. If you can explain every ADR, you can defend every part of the site.

Many organisations recommend ADRs, including [Microsoft's Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) and the [Thoughtworks Technology Radar](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records) (listed as "Adopt"). A community hub with many templates is at [adr.github.io](https://adr.github.io/).

## Status lifecycle

```
Proposed ──► Accepted ──► Superseded by ADR-NNNN
    │
    └──────► Rejected (kept for the record)
```

| Status | Meaning |
|---|---|
| **Proposed** | Drafted and open for discussion; not yet approved by Howard. |
| **Accepted** | Approved; the code should follow it. |
| **Superseded** | Replaced by a newer ADR (link both ways). The old file stays. |
| **Rejected** | Considered and declined. Keeping it shows the option was evaluated. |

Rules of thumb: one decision per ADR; keep it to 1–2 pages; don't edit an Accepted ADR's decision, write a new one instead (fixing typos and links is fine).

## Template
Copy this into `NNNN-short-title-with-dashes.md`:

```markdown
# NNNN. Title in imperative form (e.g., "Use PostgreSQL for storage")

- **Status:** Proposed | Accepted | Superseded by [NNNN](NNNN-....md) | Rejected
- **Date:** YYYY-MM-DD
- **Deciders:** Howard Isaacson

## Context
What problem are we solving? What constraints and forces apply (skills, time, cost, data shape)?
Facts only; no decision yet.

## Options considered
### Option A: ...
- Pros: ...
- Cons: ...
### Option B: ...
- Pros: ...
- Cons: ...

## Decision
"We will ..." Short, active voice.

## Consequences
What becomes easier? What becomes harder? What new risks or follow-up work does this create?

## How to explain this in an interview
2–3 sentences you could say out loud: the problem, the choice, the trade-off.

## Learn more
- 2–3 reputable links (official docs preferred).
```

## Index

| # | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-build-locally-first-with-docker-compose.md) | Build locally first with Docker Compose | Proposed |
| [0003](0003-first-data-source-noaa-swpc-real-time-solar-wind.md) | First data source: NOAA SWPC real-time solar wind | Proposed |
| [0004](0004-python-scheduled-pollers-with-raw-landing-zone.md) | Python scheduled pollers with a raw landing zone | Proposed |
| [0005](0005-postgresql-timescaledb-for-time-series-storage.md) | PostgreSQL + TimescaleDB for time-series storage | Proposed |
| [0006](0006-fastapi-for-backend-api.md) | FastAPI for the backend API | Proposed |
| [0007](0007-grafana-now-react-later-for-frontend.md) | Grafana now, React later for the frontend | Proposed |
| [0008](0008-modular-monolith-before-microservices.md) | Modular monolith before microservices | Proposed |
| [0009](0009-about-this-page-for-every-section.md) | "About this page" for every section | Proposed |
| [0010](0010-use-git-and-github-from-day-one.md) | Use git and GitHub from day one | Proposed |
| [0011](0011-cloud-deployment-target-deferred-with-criteria.md) | Cloud deployment target: defer, define criteria | Proposed |
| [0012](0012-responsive-design-mobile-and-desktop.md) | Responsive design: mobile and desktop specs | Proposed |
| [0013](0013-design-by-studying-existing-sites.md) | Design by studying existing sites | Proposed |
| [0014](0014-when-to-use-more-than-one-docker-container.md) | When to use more than one Docker container | Proposed |
| [0015](0015-where-rust-could-fit.md) | Where Rust could fit | Proposed |
| [0016](0016-data-science-workflow-as-first-class-feature.md) | Treat the data science workflow as a first-class, documented feature | Proposed |
| [0017](0017-where-ai-agents-fit.md) | Where AI agents fit in TI | Proposed |
| [0018](0018-plan-work-with-github-issues-milestones-projects.md) | Plan work with GitHub Issues, Milestones, and Projects | Proposed |
| [0019](0019-apply-sql-migrations-in-order.md) | Apply schema changes as ordered SQL files | Proposed |

Tooling (optional): [adr-tools](https://github.com/npryce/adr-tools) is a small CLI that creates numbered ADR files. Copying the template by hand works just as well.
