# 0033. Score decay forecasts only with elements from before the cutoff

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

## Context

Issue #52 asks for a time-ordered backtest of re-entry dates at 30, 7, and 1 days before the SATCAT decay date, with the error broken out by altitude band and solar activity. [ADR 0016](0016-data-science-workflow-as-first-class-feature.md) forbids a random split: the forecast must not see the future. Issue #105 forbids publishing anything derived from Space-Track. The public CelesTrak queries for a launch return the first GP and the last GP, not a daily history. The February 2022 Starlink launch (`2022-010`) is the case the issue names.

## Options considered

### A. Wait for a Space-Track history download and publish those errors

- Pros: a real track at each cutoff.
- Cons: those errors would be derived from Space-Track, which this site does not publish. The account is also empty on the machine that runs the stack.

### B. Score the public first and last GP, and leave a horizon blank when no element is near the cutoff

- Pros: the bytes are CelesTrak's public files; a missing 30-day score stays missing instead of being filled with an element from launch day.
- Cons: most objects cannot be scored, and the errors that exist are a weak baseline.

### C. Publish a single error using the last GP even when its epoch is on the decay date

- Pros: more numbers.
- Cons: that uses the orbit at or after the event to "predict" the event.

## Decision

We will use **option B**.

SATCAT `DECAY_DATE` is read as 00:00 UTC on that calendar day. A horizon of H days may use an element only when its epoch is at or before that cutoff and no more than 36 hours earlier. Two eligible elements continue the perigee slope to 120 km. One eligible element continues `MEAN_MOTION_DOT` and holds eccentricity fixed. The published table is the median absolute error in days, by horizon, altitude band, and Kp band (quiet below 4, active from 4 up to 5, storm at 5 and above). Kp is the GFZ daily maximum on the cutoff date. Objects that are still in orbit are not scored.

## Consequences

- Easier: the workflow page shows a real baseline and an honest empty cell for 30 days before decay.
- Harder: the density model in issue #51 is not in this score. A fuller track needs a source we are allowed to publish.
- The 120 km stop is a model choice. SATCAT does not give the altitude at the decay minute.

## How to explain this in an interview

“I treated the decay date as a deadline and threw away every element from after that deadline, including the one on the decay day itself. For the February 2022 launch the public record only has the first and last element set, so 30 days before decay there is nothing to score. The errors I could score are large. That is the persistence baseline, and it is supposed to be easy to beat.”

## Learn more

- [ADR 0016](0016-data-science-workflow-as-first-class-feature.md) (time-aware validation)
- CelesTrak, [A New Way to Obtain GP Data](https://celestrak.org/NORAD/documentation/gp-data-formats.php) (first and last GP queries)
- GFZ, [Kp dataset](https://doi.org/10.5880/Kp.0001) (the daily maximum used as the activity label)
