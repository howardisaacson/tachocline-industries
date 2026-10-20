# 0004. Python scheduled pollers with a raw landing zone

- **Status:** Proposed
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
SWPC and most other sources publish files over HTTP that we must **pull** on a schedule. Nobody pushes data to us. We need code that fetches, validates, and stores data reliably, and that copes with network errors, duplicate rows, and upstream format changes. Python is my strongest language and the standard for data work.

Key terms:
- **Poller:** a job that periodically requests a URL.
- **Scheduler:** what triggers jobs at set intervals.
- **Orchestrator:** a richer tool that adds retries, dependencies between steps, a UI, and run history.
- **Raw landing zone:** a folder (later object storage) where each response is saved exactly as received, before any parsing. It is also called the "bronze" layer in the *medallion* pattern (bronze = raw, silver = cleaned, gold = aggregated).

## Options considered
### A. cron + Python scripts
- Pros: simplest; built into Linux/macOS.
- Cons: awkward inside Docker; no retries or visibility; separate config outside the code.
### B. APScheduler inside a long-running Python service
- Pros: schedules defined in Python; runs as one Compose service; tiny learning curve; the stable 3.x line is mature (4.0 is still alpha as of Oct 2026).
- Cons: no built-in UI or run history; if the process dies, jobs stop (Docker's `restart: unless-stopped` helps).
### C. Prefect or Dagster (modern orchestrators)
- Pros: retries, run history, UI, and data lineage; Dagster's "assets" model fits data well; strong resume keywords.
- Cons: more concepts and infrastructure to learn before the first chart exists.
### D. Apache Airflow
- Pros: the industry incumbent.
- Cons: heavy (scheduler, webserver, metadata DB); overkill for a few feeds.

## Decision
We will write **small Python pollers** (`httpx` for HTTP, `pydantic` for validation) scheduled by **APScheduler 3.x**, running as one Docker Compose service. Every run will:
1. **Fetch** with a timeout and a descriptive `User-Agent`, and stop on 4xx errors rather than hammering the server.
2. **Land raw:** save the response unchanged to `data/raw/<source>/<YYYY-MM-DD>/<timestamp>.json`.
3. **Validate** each record against a pydantic model, counting and logging rejects.
4. **Upsert** into Postgres with `INSERT … ON CONFLICT DO UPDATE` on the natural key (idempotent).
5. **Log** a row in an `ingest_log` table: source, start/end time, HTTP status, rows received/upserted/rejected, error.

When we have 3 or more feeds, or need dependencies and backfills, we will write a new ADR to move to **Prefect or Dagster**. Keeping the fetch, parse, and load functions separate from the scheduler makes that a small change.

## Consequences
- Easier: first milestone quickly; raw files let us **replay** history if a parsing bug is found or a schema changes; `ingest_log` powers a "pipeline health" dashboard panel.
- Harder: we handle retries and alerting ourselves for now.
- Raw files grow (~2 MB per solar-wind fetch, so roughly 0.6 GB/day at a 5-min cadence). We will compress them and add a retention rule, or store only changed responses.

## How to explain this in an interview
"Each poller fetches, writes the raw response to a landing zone, validates it with pydantic, and upserts into Postgres, so reruns are idempotent and I can replay raw data if parsing changes. I deliberately started with APScheduler instead of Airflow or Dagster to get one feed working end to end, and kept the code orchestrator-agnostic so upgrading is a contained change."

## Learn more
- [APScheduler 3.x documentation](https://apscheduler.readthedocs.io/en/3.x/)
- PostgreSQL docs, [INSERT … ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)
- Databricks, [What is a medallion architecture?](https://www.databricks.com/glossary/medallion-architecture); see also [Prefect](https://docs.prefect.io/v3/get-started) and [Dagster](https://dagster.io/docs) docs
