# 0019. Apply schema changes as ordered SQL files

- **Status:** Proposed
- **Date:** 2026-10-23
- **Deciders:** Howard Isaacson

## Context
[ADR 0005](0005-postgresql-timescaledb-for-time-series-storage.md) says schema changes are numbered files in `db/migrations/`. [ADR 0014](0014-when-to-use-more-than-one-docker-container.md) says a one-shot `migrate` container applies those files and then exits, and `ingest` waits until that exit succeeds. Issue #24 adds the container. Issue #25 adds the first tables. This ADR is only about how a file gets applied.

The runner has to be safe to start twice. Scripts in the Postgres image's `docker-entrypoint-initdb.d` directory run only when the data volume is empty, so they cannot apply a file added later. A migration may contain several statements, including function bodies that use dollar quoting (`$$`). Splitting the file on semicolons would break those bodies.

## Options considered
### A. Alembic
- Pros: the usual Python migration tool; can generate migrations from SQLAlchemy models.
- Cons: our schema is SQL we write by hand (hypertables, roles), not ORM models. Alembic would be another framework to explain before the first table exists.
### B. Flyway or golang-migrate
- Pros: purpose-built; they record which versions are applied.
- Cons: a separate runtime (Java or a Go binary) in an image that is otherwise Python and `psql`.
### C. Postgres image init scripts only
- Pros: no application code.
- Cons: they do not run again when `0002_*.sql` arrives. The only way to change the schema would be to delete the data volume.
### D. A small Python runner that calls `psql`
- Pros: `psql -1 -f` runs a whole file in one transaction, dollar quotes included, and exits non-zero on error. Python decides the order and which names are new. Tests substitute a fake command runner, so CI does not need a database.
- Cons: no automatic down migrations. `CREATE INDEX CONCURRENTLY` cannot run inside the transaction that `-1` opens. We do not need either yet.

## Decision
We will apply `db/migrations/NNNN_name.sql` in numeric order with `psql`, one transaction per file. Applied filenames are stored in `schema_migrations`. A file already listed there is skipped. `schema_migrations` is the runner's bookkeeping table, created with `CREATE TABLE IF NOT EXISTS` before any numbered file runs. The solar-wind tables belong to issue #25, not to this table.

The database password is the `PGPASSWORD` environment variable. It is not a `psql` argument, because process arguments are visible to other users on the same machine.

Migration files must not open their own `BEGIN`/`COMMIT`. The runner already wraps the file. Editing a file after it has been applied is not allowed; add a new number (this matches AGENTS.md: never edit an applied migration).

## Consequences
- Easier: the migrate path is one screen of Python plus `psql`, and a failed file leaves no applied row.
- Harder: a later column is a new file. Concurrent index builds need a different path if we ever need them.
- Follow-up: issue #25 adds the first `0001_*.sql`. After a new file lands, `docker compose up --force-recreate migrate` runs the one-shot container again. A container that already exited 0 is not started a second time by a plain `docker compose up`.

## How to explain this in an interview
"Schema changes are numbered SQL files. A one-shot container applies each new file with psql inside a single transaction and records the filename, so a restart does not apply it twice. I did not use Alembic because the schema is hand-written SQL, including Timescale hypertables, and I did not use the Postgres init directory because those scripts run only on an empty data volume."

## Learn more
- PostgreSQL docs, [psql](https://www.postgresql.org/docs/current/app-psql.html) (`-1` / `--single-transaction`, and `:'variable'` as a quoted literal)
- Docker docs, [Control startup and shutdown order](https://docs.docker.com/compose/how-tos/startup-order/)
- Alembic, [tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) (the option not taken)
