# 0037. Store NEID and EXPRES solar radial velocity as meters per second

- **Status:** Proposed
- **Date:** 2026-11-05
- **Deciders:** Howard Isaacson

## Context

Issue #76 asks for high-resolution solar spectra on the site. The first slice is NEID and EXPRES only. Howard chose a radial-velocity time series, scalar columns in Postgres, and a 7-day public plot. The FITS files stay on the archive. An EXPRES day is about 1 to 2.5 GB, and one extracted spectrum is an 86 by 7920 array.

Both solar feeds are public on the NExScI Solar RV Archive. The TAP service is `https://neid.ipac.caltech.edu/TAP/sync`. The Level 2 tables are `neidsolarl2` and `expressolarl2`.

Checked 2026-11-05:

- `ccfrvmod` is km/s on both tables.
- NEID `dvrms` is km/s. A row at 2026-11-02 17:17:50 UTC was −0.6401 km/s with uncertainty 0.0003 km/s.
- EXPRES `v` and `e_v` are cm/s. A row at 2024-09-30 15:35:58 UTC was `ccfrvmod` −0.6406, `v` −64057.073, and `e_v` 19.692. `dvrms` equalled `e_v` on that row, so the TAP unit label "km/s" on EXPRES `dvrms` does not match the number.
- EXPRES Level 2 on that day ran from 2024-01-02 through 2026-04-25. A 7-day plot will often have no EXPRES line until a newer day is published.

## Options considered

### A. Download the FITS files and plot one spectrum

- Pros: the issue title says spectra.
- Cons: gigabytes per day, and the two instruments do not share one flux grid. A spectrum is not the simple time series Howard asked to start with.

### B. Store each archive's native unit and convert in the chart

- Pros: the database matches one column name.
- Cons: NEID km/s and EXPRES cm/s on one axis are wrong by a factor of 100,000 if a later query forgets which row is which.

### C. Store meters per second from `ccfrvmod`, and take the uncertainty from the column whose unit matched a sample row

- Pros: one axis, one unit, and the EXPRES `dvrms` label is not trusted over the sample.
- Cons: a later pipeline change that redefines `ccfrvmod` will not be caught until the unit guard rejects a row or a person rechecks TAP_SCHEMA.

## Decision

We will use **option C**.

`solar_rv.rv_m_s` is `ccfrvmod` times 1000. NEID `rv_error_m_s` is `dvrms` times 1000. EXPRES `rv_error_m_s` is `e_v` times 0.01. The plot clock is `obsdate` as UTC. `ccfjdsum` is stored as BJD for NEID and as JD for EXPRES, because those are the names the archive publishes. A missing RV is NULL. The poller keeps 14 days so the 7-day plot can still fill when a file arrives late. Rows older than 14 days are deleted after a successful load. The job runs once a day. It does not download FITS.

HARPS, HARPS-N, KPF, activity indices, and spectra stay on issue #76.

## Consequences

- Easier: Grafana and the home page share one SELECT of meters per second. A test can recompute the sample rows.
- Harder: EXPRES will be an empty series whenever the archive's newest public day is older than the plot window. That gap stays empty. A velocity outside ±5000 m/s, or an uncertainty outside 0 to 100 m/s, is stored as null. On the first load, 69 of 2182 NEID rows had `dvrms` 9999, and 19 of those also had velocities from about 9 to 97 km/s. Those points do not set the chart scale. The guards will not notice a forgotten factor of 1000 on a true kilometer value near 1 km/s, because 640 m/s and 0.64 m/s both sit inside the guard. The parser test is what locks the factor.

## How to explain this in an interview

"NEID and EXPRES both publish a Sun-as-a-star radial velocity, but not in the same unit. I store meters per second from the kilometer column both tables share, and I take the EXPRES uncertainty from `e_v` because a sample row showed `dvrms` was in centimeters despite its TAP label. The public chart is the last seven days. An empty EXPRES line means the archive has not published a day in that window."

## Learn more

- [Issue #76](https://github.com/howardisaacson/tachocline-industries/issues/76)
- NExScI, [Solar RV Archive help](https://neid.ipac.caltech.edu/help_solar.php) (`ccfrvmod` in km/s, `ccfjdsum` as BJD; checked 2026-11-05)
- IVOA, [TAP](https://www.ivoa.net/documents/TAP/) (the sync query this poller POSTs)
