# 0035. Show CelesTrak orbits publicly and keep Space-Track private

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

## Context

The Satellite Tracking page plots perigee from `satellite_gp`. That table can hold two writers. CelesTrak publishes current GP elements. Space-Track's user agreement says the user will not transfer data received from that site, or the analysis of it, without prior express approval. Issue #105 treats a public page and the public API as that transfer. Issue #106 asks for CelesTrak's terms before a CelesTrak-derived plot is shown. The terms are written in [data-licenses.md](../research/data-licenses.md).

## Options considered

### A. Leave the table untagged and keep the public chart

- Pros: no migration.
- Cons: a later `gp_history` load would publish Space-Track altitudes. Issue #109's own acceptance line forbids that.

### B. Tag each row, and have public routes return `celestrak` only

- Pros: Grafana on localhost can still see Space-Track. The public chart cannot.
- Cons: rows written before the tag, on a machine that already loaded `gp_history`, cannot be split, so they are labeled `unknown` and stay off the public API.

### C. Stop storing Space-Track at all

- Pros: nothing private is in Postgres.
- Cons: the private decay check the agreement still allows would have to live somewhere else.

## Decision

We will use **option B**.

`satellite_gp.provider` is `celestrak`, `spacetrack`, or `unknown`. The CelesTrak poll writes `celestrak`. The Space-Track poll writes `spacetrack` and does not replace a `celestrak` tag on the same epoch. A later CelesTrak write may replace `spacetrack`. `GET /api/v1/satellite-perigee` and `GET /api/v1/satellite-decay` add `provider = 'celestrak'`. The decay query filters before the window function, so a public rate is not a step from a Space-Track neighbor.

Existing rows are labeled `celestrak` only when `ingest_log` has no successful `gp-hist-*` run. Otherwise they are `unknown`.

CelesTrak's [usage policy](https://celestrak.org/usage-policy.php) (updated 2026 May 22) is an access rule: download only what you need, once per update, and stop on any HTTP status other than 200. The public chart credits CelesTrak. That policy is not a copyright license and not a Department of Defense approval for this site to redistribute Space-Track data. No email was sent to Space-Track asking for an exception.

## Consequences

- Easier: the public page can keep showing the five satellites we poll from CelesTrak.
- Harder: a model trained on Space-Track history must not be published either. This ADR does not build that guard in the analysis code, because that code does not read Space-Track today.

## How to explain this in an interview

"Two feeds can land in one table. I store who wrote the row. The public API has a WHERE clause for the feed we are allowed to show. Space-Track's agreement forbids handing the data, or an analysis of it, to the public, so those rows stay on localhost."

## Learn more

- [CelesTrak usage policy](https://celestrak.org/usage-policy.php) (checked 2026-11-01)
- Space-Track, [documentation](https://www.space-track.org/documentation) (the user agreement is on that site)
- PostgreSQL, [`INSERT` ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html) (the tag survives a conflicting write)
