# 0020. Show space weather as four radial time plots, not time-on-x line charts

- **Status:** Proposed
- **Date:** 2026-10-27
- **Deciders:** Howard Isaacson

## Context
[SpaceWeatherLive](https://www.spaceweatherlive.com/) already shows the charts we first planned: time on the x-axis and an activity value on the y-axis. Copying them would make TI look like a clone and would not show anything new. Howard wants a different way to present the data. The idea: four radial (polar) plots, one for each timescale, where the angle is time and the distance from the center is the activity.

The design follows the SpaceX-style frontend chosen in [design_survey.md](../research/design_survey.md). A radial plot also fits the Sun's roughly 11-year cycle, which is itself a circle of repeating activity.

## Options considered
### A. Standard line charts, time on x (what SpaceWeatherLive does)
- Pros: familiar; easy to read exact values; Plotly and Grafana do it out of the box.
- Cons: not distinctive; long ranges squeeze detail; no sense of repetition.
### B. Four radial plots (Howard's idea)
- Pros: distinctive; shows cycles and repetition at four zoom levels side by side; fills a square or circular tile well on mobile; tells the "Sun is a clock" story.
- Cons: angles and radii are harder to read than a flat axis; each plot's radius changes scale, so plots are not directly comparable by length; Plotly cannot fade a line segment by segment on its own, so the fade effect may need extra work; needs a text or table alternative for accessibility.
### C. Both: radial plots as the hero, line charts in a detail view
- Pros: distinctive front page plus exact readings for people who want them.
- Cons: more to build and test.

## Decision
Build **option B as the main visual**, with a plain data table and CSV download beside each plot, which gives some of the benefit of option C at low cost. Add full line charts later only if the radial plots prove hard to read.

The agreed design rules (decided with Howard 2026-10-27):
1. **Four plots**, each a full circle for one timescale: **one day, one month, one year, 11 years**.
2. **Angle is time.** Zero is at the top (12 o'clock). Time runs **clockwise** like a clock.
3. **Radius is the activity indicator.** The first indicator is the **Kp index** (geomagnetic activity). Other indicators (X-ray flux, sunspot number, satellite altitude or drag) can follow once the Kp version works.
4. **Radius auto-scales.** The largest value in the current window is drawn at the edge of the circle, so the trace never leaves the circle. The scale is always labeled with ring lines, and the maximum is written on each plot.
5. **Radar-sweep behavior.** A bright "now" head moves clockwise. The trace stays on the plot until the head comes around and overwrites it with the next period's data. The older the data, the more it fades, like the afterglow on a radar screen.
6. **Window.** Each circle shows the most recent window (last 24 hours, 30 days, 365 days, 11 years), with the oldest data at the start angle.

### Open point for Howard to confirm
Rules 5 and 6 pull in slightly different directions. If the oldest data always sits at 12 o'clock, the whole trace shifts a little with each update and nothing is ever "overwritten". If data stays at a fixed angle until the head returns and overwrites it, the start angle has to be a fixed moment. **Recommendation:** use the overwrite behavior with a fixed lap start, using UTC boundaries: midnight for the day plot, the 1st of the month for the month plot, 1 January for the year plot, and the start of the current solar cycle (or a fixed 11-year grid) for the 11-year plot. The window is then "the most recent lap plus the part of the last lap not yet overwritten", which is still the most recent period of that length, and 12 o'clock is where the oldest data starts at first fill. Confirm or change this before building.

### Suggested data per plot (to check during Phase 1)
| Plot | Window | Suggested data | Points |
|---|---|---|---|
| Day | 24 hours | 1-minute estimated Kp, averaged into 5- or 10-minute bins | about 144 to 288 |
| Month | 30 days | 3-hourly Kp | about 240 |
| Year | 365 days | daily maximum (and mean) of Kp | 365 |
| 11 years | about 11 years | monthly or daily aggregate of Kp | 132 to about 4,000 |

Both Kp feeds are verified in [data_sources.md](../research/data_sources.md) (the 1-minute estimated feed and the 3-hourly feed). TI only stores what it has collected, so the year and 11-year plots will be mostly empty at first. A longer Kp history would have to be back-filled from another source, which is a research task still to do. Until then, draw the empty part of the circle as an empty track and label where TI's own data begins. Do not fill it with made-up values.

### Display and build notes
- Plotly's polar charts (`scatterpolar`) can set the zero angle at the top and the direction to clockwise. Fading a trace by age probably needs many short segments, per-point marker opacity, or a custom canvas or SVG drawing with D3. Decide in a short spike before building.
- Color the trace by NOAA's G-scale (Kp 5 and above is G1 or higher) so a quiet day with a small maximum doesn't look as dramatic as a storm. An optional "fixed 0–9 scale" switch would let people compare plots fairly.
- Layout follows [ADR 0012](0012-responsive-design-mobile-and-desktop.md): a 2×2 grid at 1024 px and wider, a single column below 640 px, with the day plot first. Test both on mobile and desktop.
- Every plot gets a hover or tap readout, a data table, a CSV download, and an "About this page" link ([ADR 0009](0009-about-this-page-for-every-section.md)) that explains how to read a radial plot.

## Consequences
- Easier: a recognizable, original front page; one picture shows four timescales; matches the solar-cycle story.
- Harder: values are harder to read than on a line chart; auto-scaling means plots aren't comparable by length; more custom front-end work; needs extra accessibility work and a long-range Kp history.
- We still need the data pipeline first ([issue #23](https://github.com/howardisaacson/tachocline-industries/issues/23)).

## How to explain this in an interview
"Most space-weather sites plot activity against time on a flat axis, so I tried a polar layout instead. Angle is time and the radius is the Kp index, with four rings for a day, a month, a year and a solar cycle. The radius auto-scales so the trace always fits, which makes plots hard to compare by length. I handled that by labeling the scale, coloring by NOAA's storm levels and offering a data table and CSV for exact values."

## Learn more
- Plotly, [Polar charts in Python](https://plotly.com/python/polar-chart/) (the same options exist in Plotly.js)
- Plotly.js, [scatterpolar traces](https://plotly.com/javascript/reference/scatterpolar/)
- NOAA SWPC, [Planetary K-index](https://www.swpc.noaa.gov/products/planetary-k-index)
- NOAA SWPC, [Space weather scales (G, S, R)](https://www.swpc.noaa.gov/noaa-scales-explanation)
