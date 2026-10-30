# 0027. Ship the 11-year radial Kp ring using GFZ history since 1932

- **Status:** Proposed
- **Date:** 2026-10-29
- **Deciders:** Howard Isaacson
- **Supersedes:** [0020](0020-radial-time-plots-for-space-weather.md)

## Context
[ADR 0020](0020-radial-time-plots-for-space-weather.md) chose radial Kp plots and **deferred** the fourth ring (11 years) until a long Kp history existed. [ADR 0022](0022-store-gfz-kp-apart-from-swpc-estimates.md) now stores GFZ definitive 3-hour Kp since 1932, and `GET /api/kp-gfz` serves it. The public page already draws an “11 years” ring from that feed. The written decision still said “deferred,” which is wrong and confusing in interviews.

## Options considered
### A. Leave ADR 0020 as Accepted and only update the survey
- Pros: fewer ADR files.
- Cons: Accepted decision text would still say deferred; AGENTS.md forbids editing an Accepted decision body.
### B. New ADR that supersedes 0020 and keeps four radial timescales
- Pros: history stays readable; code and docs match; still one clear visual language.
- Cons: readers must follow the supersession link.
### C. Drop the 11-year ring from the UI until a separate product review
- Pros: matches old ADR literally.
- Cons: throws away the GFZ work visitors can already see.

## Decision
We will use **option B**. This ADR **supersedes [0020](0020-radial-time-plots-for-space-weather.md)**.

The public space-weather page shows **four** radial Kp clocks:

| Plot | Window | Data |
|---|---|---|
| One day | 24 hours | SWPC 1-minute estimated Kp (binned) |
| 30 days | 30 days | GFZ 3-hour Kp |
| One year | 365 days | Daily max of GFZ 3-hour Kp |
| 11 years | 11 × 365 days from 1 Jan 1932 | Daily max of GFZ 3-hour Kp (nowcasts may appear until the daily file replaces them) |

All other rules from ADR 0020 stay: angle is time (12 o’clock start, clockwise), radius is Kp with auto-scale (optional fixed 0–9), radar-sweep overwrite on UTC lap boundaries, SVG drawing ([ADR 0021](0021-react-vite-page-with-svg-radial-plots.md)), table + CSV per plot, layout per [ADR 0012](0012-responsive-design-mobile-and-desktop.md) (day first; single column &lt; 640 px; row layout at ≥ 1024 px with room for four tiles).

## Consequences
- Easier: docs match the live page; the solar-cycle story is visible.
- Harder: four tiles on small screens make a tall page; GFZ nowcasts on the long ring must stay labelled as such in the About page.
- ADR 0020 remains in the tree as Superseded for history.

## How to explain this in an interview
"We deferred the 11-year ring until we had a real long Kp series. Once GFZ definitive Kp since 1932 was in the database, we shipped the fourth clock and superseded the old ADR so the written decision matches production."

## Learn more
- GFZ, [Kp index](https://kp.gfz.de/en/)
- [ADR 0022](0022-store-gfz-kp-apart-from-swpc-estimates.md)
- [docs/about/space-weather.md](../about/space-weather.md)
