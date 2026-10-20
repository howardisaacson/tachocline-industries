# 0003. First data source: NOAA SWPC real-time solar wind

- **Status:** Proposed
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
The first milestone is one data feed end to end (poll → store → chart). The feed should be free, need no account, update often, be genuinely satellite-based, and fit the site's theme. (The *tachocline* is the layer inside the Sun thought to drive the solar dynamo, the engine behind solar activity.) Research is in [`../research/data_sources.md`](../research/data_sources.md).

NOAA's Space Weather Prediction Center (SWPC) publishes real-time **solar wind** data measured by spacecraft at the L1 point, about 1.5 million km toward the Sun. The wind reaches Earth roughly 15–60 minutes later, so this is the early warning for geomagnetic storms.

Important 2026 changes, verified 2026-10-18:
- **DSCOVR has been retired as a real-time source.** SWPC stopped ingesting DSCOVR data on 2026-06-30. **SOLAR-1** (NOAA's SWFO-L1 satellite, launched 2025-09-24, operational 2026-06-10) is now primary. **ACE** is the backup until NASA's **IMAP** (I-ALiRT) has 24/7 coverage.
- The old endpoints (`services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json`, `mag-7-day.json`, etc.) were **deprecated and removed around 2026-04-30** and now return 404. Many tutorials still use them.
- The replacements are `json/rtsw/rtsw_wind_1m.json` (plasma: speed, density, temperature), `rtsw_mag_1m.json` (magnetic field, incl. Bz), and `rtsw_ephemerides_1h.json`. Each row has `time_tag`, `source` (e.g., `SOLAR1`, `ACE`, `IMAP`), and an `active` flag marking the spacecraft forecasters are using.
- **They only contain about the last 24 hours** (2,876 rows across 3 spacecraft when checked). To show a week or a month, **we must store our own history.**

## Options considered
### A. SWPC real-time solar wind (`json/rtsw/*`)
- Pros: no auth; 1-minute data; small JSON; strong theme fit; real data-engineering problems (rolling window, multi-source rows, deduplication).
- Cons: endpoints changed recently and may change again; no quality flags yet.
### B. GOES X-ray flux (SWPC)
- Pros: just as simple; flares are visually dramatic.
- Cons: a single spacecraft and less to model. Better as feed #2 on the same server.
### C. CelesTrak orbital elements
- Pros: popular, and leads to live satellite tracking.
- Cons: updates only every 2 h, strict rate limits, and needs orbit propagation math first.
### D. NASA FIRMS fires
- Pros: geospatial and visually strong.
- Cons: needs a key for the API, has larger files, and needs PostGIS. Better later.

## Decision
We will use **SWPC `rtsw_wind_1m.json` and `rtsw_mag_1m.json`** as the first source. We will store **every spacecraft's rows** keyed by `(time_tag, source)`, keep the `active` flag, and chart the active source by default. We will poll every 5 minutes. That is well inside the 24 h window, so a missed run loses nothing.

## Consequences
- Easier: a fast first milestone with no credentials.
- Harder: we own history, so the poller must be **idempotent** (re-inserting the same rows changes nothing).
- Risk: future schema or endpoint changes. Mitigations: validate responses with a schema, log failures, and keep the raw JSON ([ADR 0004](0004-python-scheduled-pollers-with-raw-landing-zone.md)).
- Gaps while my laptop is off are possible. Long history can be backfilled from NOAA NCEI archives later.

## How to explain this in an interview
"My first feed was NOAA's real-time solar wind from the SOLAR-1 and ACE spacecraft at L1. Mid-2026 NOAA retired DSCOVR and removed the old 7-day endpoints, and the new files only hold about 24 hours, so I built idempotent ingestion that upserts on time plus spacecraft and builds its own long-term history. That was a real example of an upstream schema change I had to adapt to."

## Learn more
- SWPC, [Solar Wind Observations](https://www.swpc.noaa.gov/products/solar-wind) (Data tab describes the JSON files)
- SWPC, [Solar Wind Data and Display Changes](https://www.spaceweather.gov/news/solar-wind-data-and-display-changes) (DSCOVR → SOLAR-1)
- NWS, [Service Change Notice 26-21](https://www.weather.gov/media/notification/pdf_2026/scn26-21_Data_Format_Changes_Impacting_SWPC_Products.pdf) (deprecated endpoints and replacements)
