# 0023. Backfill GP history from Space-Track and serve the perigee rate

- **Status:** Proposed
- **Date:** 2026-10-27
- **Deciders:** Howard Isaacson

## Context
CelesTrak gives the current element set. Polled every two hours, it builds history only after the poller has been running. A decay rate needs two epochs. Space-Track's `gp_history` class has the earlier sets for the same catalog numbers, behind a free account. The fields match the OMM names already stored in `satellite_gp`.

The Orbit decay dashboard already computes kilometers per day in its own SQL. `GET /api/satellite-perigee` returns the altitudes and not the rate.

## Options considered
### A. Keep waiting for the two-hour poll to accumulate epochs
- Pros: no account, no second download.
- Cons: a new database has one point per satellite, so the rate is empty.
### B. Daily `gp_history` for the last 400 days when credentials exist, plus `GET /api/satellite-decay`
- Pros: the same table and the same two-body altitude. Empty credentials skip the job instead of failing the container. The rate uses the previous epoch even when it sits just outside the requested window.
- Cons: the history does not load until Howard puts a Space-Track account in `.env`. The query is the last 400 days, not the full catalog back to the 1950s.

## Decision
We will use **option B**. Login is one POST to `https://www.space-track.org/ajaxauth/login`. The password is form data, not a URL and not a log line. Each catalog number is one GET of `class/gp_history`, saved raw, then upserted on `(epoch, norad_cat_id)` with the same altitude function as the CelesTrak rows. Feed names are `gp-hist-<norad>`, so the 5-minute health stat keeps ignoring them.

`GET /api/satellite-decay` returns `km_per_day`. The SQL looks 14 days before `from` so the first point in the window can see the previous epoch. A negative rate means perigee is falling.

## Consequences
- Easier: a satellite page can plot a rate as soon as two epochs exist. Re-running the file updates the same keys.
- Harder: without the account, only the live CelesTrak poll adds epochs. 400 days is a choice; a longer backfill would be a later change to that constant.

## How to explain this in an interview
"The live GP poll is the current element set. History comes from Space-Track once a day, into the same table, and only if the account is configured. The decay route is a SQL window: perigee now minus perigee last time, divided by the days between them. The lookback is outside the caller's window so the first point is not dropped."

## Learn more
- Space-Track, [documentation](https://www.space-track.org/documentation) (the query example uses `/basicspacedata/query/class/gp/...`)
- Space-Track, [`gp_history` columns](https://www.space-track.org/basicspacedata/modeldef/class/gp_history/format/html)
- PostgreSQL, [window functions](https://www.postgresql.org/docs/current/tutorial-window.html)
