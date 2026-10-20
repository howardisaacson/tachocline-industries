# 0014. When to use more than one Docker container

- **Status:** Proposed
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
Howard asked: *jump2 uses a set of Docker containers and SkyPortal uses two, so when do we need more than one?* This is a common interview question and directly shapes our `docker-compose.yml`.

**Real examples**
- **SkyPortal** (an open-source astronomy data platform). Its [`docker-compose.yaml`](https://github.com/skyportal/skyportal) (checked 2026-10-20 on `main`) defines **two long-running services**: `web` (the application, built from the repo) and `db` (PostgreSQL 17, using the `pgvector/pgvector:pg17` image), plus a **one-shot `db-init`** container. `db-init` uses the app image, creates the schema, then exits; `web` waits for it to finish, and it waits for the database health check. Inside the `web` container SkyPortal runs several processes (web servers, workers) under one supervisor, which is a deliberate "fat app container" choice.
- **jump2** (California Planet Search; private repo, contents not verified here). Howard reports it uses **a set of containers**. Generically, such systems split into something like a web app, a database, and background or processing services, but we won't claim specifics.

**The principle.** A container should wrap **one concern**: something with its own **lifecycle** (start, stop, upgrade, restart independently), **scaling** needs, **dependencies or base image**, or **resource and security** profile. Docker's docs recommend separating areas of concern, generally one service per container. "One *process* per container" is a rule of thumb, not dogma: an app container may run a web server plus workers under a supervisor (as SkyPortal's does) when they always deploy together.

Split into separate containers when parts:
- are **different software** (Postgres vs your Python app vs Grafana): never bake the database into the app image;
- **restart or deploy at different times** (redeploy the API without restarting the DB);
- **scale differently** (many workers, one DB);
- **fail differently** (a crashing poller shouldn't take down the dashboard);
- run **one-off jobs** (migrations/init, like SkyPortal's `db-init`).

Keep things together when they always ship, scale, and fail together, and splitting would only add network plumbing.

## Options considered
### A. One container running everything (DB + pollers + API + Grafana)
- Pros: one thing to start.
- Cons: can't upgrade or restart parts independently; mixes base images; a big anti-pattern for databases.
### B. One container per concern (Compose services)
- Pros: matches each component's lifecycle; uses official images for Postgres and Grafana; clear logs per service.
- Cons: some networking and startup-order configuration.
### C. Many fine-grained services (per data source, gateway, queue…)
- Pros: maximum isolation.
- Cons: the microservice premium without the need ([ADR 0008](0008-modular-monolith-before-microservices.md)).

## Decision
Use **one container per concern** (option B). TI maps to:

| Service | Image | Why separate |
|---|---|---|
| `db` | `timescale/timescaledb` (Postgres) | Stateful; named volume; upgraded rarely; health-checked |
| `migrate` | our app image, one-shot | Applies `db/migrations`, then exits (like SkyPortal's `db-init`) |
| `ingest` | our Python image | Long-running scheduler; restarts independently; may scale or split by source later |
| `api` | our Python image (same or similar) | Web server; redeployed often; may scale separately |
| `grafana` | `grafana/grafana` | Third-party app with its own state and upgrades |
| `web` (Phase 3) | Node build → static files | Different toolchain (JavaScript) |

All pollers stay in **one** `ingest` container until a real reason (resource use, failure isolation) justifies splitting.

## Consequences
- Easier: independent restarts and upgrades, clean logs, official images.
- Harder: `depends_on` with health checks, service-name networking, and shared env config to learn.

## How to explain this in an interview
"I split containers by concern, meaning things with different lifecycles, scaling, or dependencies: the database, a one-shot migration job, the ingest scheduler, the API, and Grafana. That's similar to SkyPortal, which runs an app container and a Postgres container plus a one-shot init. I didn't split further, because separate containers per data source would add network complexity without a lifecycle or scaling reason."

## Learn more
- Docker docs, [Run multiple processes in a container](https://docs.docker.com/engine/containers/multi-service_container/) and [Building best practices](https://docs.docker.com/build/building/best-practices/)
- Docker docs, [Control startup order](https://docs.docker.com/compose/how-tos/startup-order/)
- SkyPortal, [GitHub repo](https://github.com/skyportal/skyportal) and [setup docs](https://skyportal.io/docs/setup.html)
