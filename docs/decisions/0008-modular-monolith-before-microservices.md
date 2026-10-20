# 0008. Modular monolith before microservices

- **Status:** Proposed
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
"Microservices" is a common interview topic and a tempting thing to put on a portfolio. I want to understand it well enough to discuss it honestly, and to choose an architecture that fits a one-person project.

**What microservices are:** a system split into small services that are **independently deployable**, each owning **one business capability and its own data** (its own database), and talking to the others over the network (HTTP APIs or message queues). Different teams can build, release, and scale their own service without coordinating with everyone else.

**What they cost** (Martin Fowler calls this the "microservice premium"): network calls that can fail or slow down, data spread across databases (no simple joins or transactions), distributed tracing and logging, versioned APIs between services, and much more deployment and monitoring work.

**When they make sense:** many teams working on one product, parts with very different scaling or reliability needs, or a large codebase where coordinating releases has become a real bottleneck. Fowler's "Monolith First" advice is to start with a well-structured monolith and split it only when those pressures appear.

**A modular monolith:** one codebase with clear internal boundaries (modules with defined interfaces), so it *could* be split later.

## Options considered
### A. True microservices (a service plus its own database per source, a message broker, an API gateway)
- Pros: impressive buzzwords; teaches distributed-systems problems.
- Cons: all the premium with none of the benefits (one developer, tiny load); slows learning of fundamentals; hard to defend honestly ("why did one person need eight databases?").
### B. One single process doing everything
- Pros: simplest.
- Cons: a crash in polling takes down the API; can't restart or scale parts separately.
### C. Modular monolith, run as a few Docker services
- Pros: one repo and one shared database; clear modules (`ingest/`, `api/`, `db/`, `dashboards/`) with defined interfaces; pollers, API, and Grafana run as separate containers, so one can fail or restart without the others; easy to reason about and explain.
- Cons: the services share one database, so they aren't independent in the microservices sense. That is a deliberate trade-off.

## Decision
We will build a **modular monolith** in one repository, deployed as a small number of **Docker Compose services** (`db`, `ingest`, `api`, `grafana`, later `web`) that share one PostgreSQL database. Modules communicate through well-defined interfaces: Python functions inside a service, SQL tables and views between `ingest` and `api`, and HTTP between `web` and `api`. We will **not** call this microservices. We will revisit with a new ADR if a real driver appears, e.g. a component needing independent scaling or a streaming source better served by a message queue.

## Consequences
- Easier: development, debugging, and testing; time goes into data engineering instead of plumbing.
- Harder: nothing important at this scale. The shared database couples `ingest` and `api` schemas, so we treat the DB views as a contract.
- Interview value: I can explain microservices, their costs, and why I didn't use them. That is a stronger answer than having used them without need.

## How to explain this in an interview
"It's a modular monolith: one repo and one Postgres database, but split into separate containers for ingestion, the API, and dashboards, with clean module boundaries. Microservices solve organisational and scaling problems I don't have as a one-person project, so I avoided the operational cost but kept the seams where a split would happen if, say, ingestion needed to scale independently."

## Learn more
- Martin Fowler, [Microservices](https://martinfowler.com/articles/microservices.html), [MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html), and [Microservice Premium](https://martinfowler.com/bliki/MicroservicePremium.html)
- Chris Richardson, [Microservice architecture pattern](https://microservices.io/patterns/microservices.html)
- Shopify Engineering, [Deconstructing the Monolith](https://shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity) (a modular monolith at scale)
