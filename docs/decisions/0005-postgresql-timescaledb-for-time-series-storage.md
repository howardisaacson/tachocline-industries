# 0005. PostgreSQL + TimescaleDB for time-series storage

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
Most of our data is **time series**: a timestamp plus measurements, arriving every minute, forever. Solar wind alone is ~1,440 rows/day per spacecraft. Later sources add other shapes: orbital elements (relational), fire detections (geospatial points), event catalogs (nested JSON). We need storage that handles fast time-range queries ("last 7 days, averaged per hour"), works locally in Docker, is free, and teaches skills employers ask for. SQL is the most transferable database skill.

Key terms:
- **Relational database:** tables with rows and columns, queried with SQL.
- **TimescaleDB:** a free extension that adds time-series features to PostgreSQL. Its docs now live at Tiger Data, the company formerly called Timescale.
- **Hypertable:** a normal-looking table that Timescale automatically splits into time chunks for speed.
- **Continuous aggregate:** a precomputed, auto-refreshing rollup (e.g., hourly averages).

## Options considered
### A. SQLite
- Pros: zero setup; a single file; great for learning SQL.
- Cons: one writer at a time; weak with several services (poller + API + Grafana) hitting it at once; few time-series features; we would migrate within weeks.
### B. Plain PostgreSQL
- Pros: rock-solid, the most in-demand open-source database, full SQL, JSONB, PostGIS for geospatial.
- Cons: big time-series tables need manual partitioning, rollups, and retention.
### C. PostgreSQL + TimescaleDB
- Pros: everything in B, plus hypertables, `time_bucket()`, continuous aggregates, compression, and retention policies; still standard SQL; Grafana's built-in PostgreSQL data source supports it.
- Cons: one more concept; some advanced features have licence nuances (check the docs).
### D. InfluxDB
- Pros: purpose-built for metrics; popular with Grafana.
- Cons: not general-purpose (awkward for orbits, events, joins); its query languages have changed across major versions; a less transferable skill than SQL.
### E. Cloud warehouse (BigQuery, Snowflake)
- Pros: great for large analytics; strong resume keywords.
- Cons: not local; costs money; built for batch analytics, not minute-level operational reads. Possibly a later export target.

## Decision
We will use **PostgreSQL with the TimescaleDB extension** (official `timescale/timescaledb` Docker image), with schema changes tracked as numbered migration files in `db/migrations/`. Time-series tables become hypertables with natural primary keys (e.g., `(time_tag, source)`). We will add continuous aggregates for hourly and daily views, and enable **PostGIS** when geospatial sources arrive.

## Consequences
- Easier: one database for all data shapes; SQL skills transfer to any job; Grafana and FastAPI both connect directly.
- Harder: learning Postgres basics (roles, indexes, `EXPLAIN`) plus Timescale specifics.
- If Timescale ever becomes a problem, the data is still plain Postgres tables, so falling back to option B is low-risk.

## How to explain this in an interview
"I chose Postgres with TimescaleDB because my data is mostly minute-level time series but also relational and, later, geospatial. Timescale gives me automatic time partitioning and precomputed rollups while I keep standard SQL, joins, and PostGIS in one database. I considered InfluxDB, but that would have meant a second, less general system."

## Learn more
- [PostgreSQL documentation](https://www.postgresql.org/docs/current/)
- TimescaleDB (Tiger Data) docs, [Hypertables](https://www.tigerdata.com/docs/learn/hypertables/understand-hypertables) and [Continuous aggregates](https://www.tigerdata.com/docs/learn/continuous-aggregates)
- SQLite, [Appropriate uses for SQLite](https://www.sqlite.org/whentouse.html) (when SQLite *is* the right choice)
