# 0036. Plain-language Kp sentences from fixed rules

- **Status:** Proposed
- **Date:** 2026-11-05
- **Deciders:** Howard Isaacson

## Context

Issue #96 asks for one sentence under each radial Kp plot so a visitor can tell, without reading the ring, whether the stretch they are looking at is quiet or busy for that stretch. The issue offers two ways to write the sentence. It also asks for an API object that carries the sentence and the statistics, and for an About section that shows the method.

The four plots are not the same product. The day ring is SWPC's 1-minute estimated Kp. The 30-day, 1-year, and 11-year rings are GFZ 3-hour Kp ([ADR 0022](0022-store-gfz-kp-apart-from-swpc-estimates.md)). A sentence that mixed those products would compare an estimate with the definitive index.

## Options considered

### A. Fixed rules, computed when the page asks

- Pros: no API key, the same rows always produce the same sentence, and a test can check every number. The statistics function can later be handed to the briefing agent (#43).
- Cons: the wording is stiff. It will not mention a flare or a news event unless that fact is one of the numbers we already store.

### B. An agent writes the sentence from those statistics

- Pros: the prose can be smoother.
- Cons: it can state a number it was not given. It needs an eval set, a spend cap, and a fallback. That is the work in #43, not this issue.

### C. A scheduled job writes the sentence every few hours

- Pros: the page would read a stored string.
- Cons: a second clock, and a sentence that can lag the rows the rings are drawing.

## Decision

We will use **option A**. Option B stays with #43. The route does not wait on a schedule. `GET /api/v1/kp-interpretation` aggregates the stored rows and returns the four sentences. Optional `span` keeps one of them.

The label is how far the current mean sits from the mean of the baseline windows, in population standard deviations. Population, because those windows are the whole comparison set, not a sample of a larger one.

| Score | Words |
|---|---|
| more than 1 SD below | well below average |
| from 1 SD below up to 0.5 SD below | below average |
| within 0.5 SD, either side | about average |
| from 0.5 SD above up to 1 SD above | above average |
| more than 1 SD above | well above average |

A standard deviation of zero means every baseline window had the same mean. The label is then about average, above, or below. It is never "well", because there is no spread to be well outside of.

| Plot | Current mean | Baseline | Covered when |
|---|---|---|---|
| Day | today's SWPC 1-minute Kp | the 7 previous UTC days | a finished day has at least 720 samples (12 hours). Today can be described after 60 samples, and the sentence says "so far" |
| 30 days | the last 30 days of GFZ Kp | the 12 blocks of 30 days before that | at least half the days have 4 of the 8 three-hour slots, and all 12 blocks pass |
| 1 year | the last 365 days of GFZ Kp | each complete calendar year since 1932 that ended before this window | same half-day rule, and at least 10 such years |
| 11 years | the last 11 × 365 days of GFZ Kp | each earlier block of that length back to 1 January 1932 | same half-day rule, and at least 3 such blocks |

The 11-year blocks use the ring's length. They are not solar-cycle minima. Those dates are a different series, and this ring is not drawn on them.

A GFZ day counts toward coverage only when it has at least 4 of the 8 slots. The mean still uses every stored slot. If the current window or the baseline is short, the sentence says so and does not pick a label. A Kp of 5 or more adds the peak, the NOAA G-scale, and the UTC time of that peak. Numbers in the sentence are the statistics rounded to two decimal places. The year sentence also says the percent of earlier years whose mean is strictly lower. That percent is rounded to the nearest whole number.

## Consequences

- Easier: the page can show a sentence that a test can recompute. #43 can call the same function and is not allowed to invent a different number.
- Harder: the wording will not mention context we do not store. The GFZ aggregate reads one row per day since 1932 on each call. That is about 35,000 short rows, which is acceptable on this machine and would want a summary table if the call got slow.

## How to explain this in an interview

"The sentence is a function of the stored means, not a model. I place today's mean among the last seven days and label it from the population standard deviation, and I do the same for 30 days, 365 days, and 11 years against GFZ. If the table does not cover half the window, the sentence says the record is too short. An interviewer might ask why the standard deviation is the population one: the baseline is the whole set of windows on the page, not a sample I plan to generalize."

## Learn more

- [Issue #96](https://github.com/howardisaacson/tachocline-industries/issues/96)
- NOAA, [NOAA Space Weather Scales](https://www.spaceweather.gov/noaa-scales-explanation) (G1 starts at Kp 5; checked 2026-11-05)
- Python docs, [`statistics.pstdev`](https://docs.python.org/3/library/statistics.html#statistics.pstdev) (population standard deviation)
