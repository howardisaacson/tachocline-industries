# 0032. Record a sha256 manifest beside each Drag Watch raw file

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

## Context

Issue #49 is the first Drag Watch step: the bytes used later for a decay model must be traceable. [ADR 0016](0016-data-science-workflow-as-first-class-feature.md) already says raw files stay immutable and carry a manifest with source, URL, retrieval time, and sha256. [ADR 0004](0004-python-scheduled-pollers-with-raw-landing-zone.md) already lands responses under `data/raw/<source>/<date>/` before parsing. Those files had no hash record. Space-Track `gp_history` and the GFZ Kp/ap/F10.7 file were already downloaded. CelesTrak SATCAT decay dates were not.

## Options considered

### A. One JSON sidecar next to each raw file

- Pros: the hash travels with the bytes; a re-run does not need Postgres; the password never has to be in the file if the URL is the public query.
- Cons: two files per download; a reader has to open the sidecar to see the URL.

### B. One append-only `manifest.jsonl` per source

- Pros: one place to scan every download.
- Cons: a partial append can corrupt the only copy of the history; the hash is no longer beside the file it names.

### C. A Postgres provenance table only

- Pros: queryable next to `ingest_log`.
- Cons: if the database is down, the landed file has no record, which is the case the raw zone is meant to survive.

## Decision

We will use **option A** for the three Drag Watch inputs in issue #49.

Each successful landing of Space-Track `gp_history`, a CelesTrak SATCAT record, or the GFZ `Kp_ap_Ap_SN_F107_since_1932.txt` file writes `<raw filename>.manifest.json` with `source`, `product`, `url`, `retrieved_at`, `sha256`, and `bytes`. The hash is SHA-256 of the response body. SATCAT is fetched once a day for the five tracked catalog numbers and is not upserted. The starter set had no decay dates on the last catalog check; the `DECAY_DATE` field is still stored as published.

## Consequences

- Easier: a later model can point at a file and show the URL and hash it came from.
- Harder: other pollers do not write a manifest until they pass a URL into `write_raw`.
- SATCAT rows are not in Postgres yet. A decay date in the raw file is not a column on `satellite_gp`.

## How to explain this in an interview

“Before I fit a decay model I keep the download unchanged and write a sidecar with the URL, the time, and a SHA-256 of those bytes. If someone asks whether a Kp file or a decay date was edited, I recompute the hash. SATCAT is saved even when the decay date is still blank, because that blank is the catalog’s answer on that day.”

## Learn more

- Python, [`hashlib`](https://docs.python.org/3/library/hashlib.html) (SHA-256)
- [ADR 0004](0004-python-scheduled-pollers-with-raw-landing-zone.md) (raw landing zone)
- [ADR 0016](0016-data-science-workflow-as-first-class-feature.md) (provenance in the data science workflow)
