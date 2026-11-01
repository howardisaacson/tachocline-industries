# 0029. Offer a radial↔Cartesian “Change Data View” unwind on each Kp plot

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

## Context
[ADR 0027](0027-eleven-year-kp-ring-with-gfz.md) (and earlier [ADR 0020](0020-radial-time-plots-for-space-weather.md)) keep radial Kp clocks as the distinctive default. Exact reading is already helped by the table, CSV, and under-plot readout. Some visitors still want a familiar time-on-x chart. [ADR 0020](0020-radial-time-plots-for-space-weather.md) considered “both” as option C and deferred full line charts. Issue #94 asks for a per-plot toggle that **animates** the same SVG points from the circle into a Cartesian series and back, like a rotary telephone dial spinning home.

## Options considered
### A. Keep radial only; rely on table + CSV
- Pros: already shipped; no animation work.
- Cons: no familiar chart for interviewers who expect time on x.

### B. Separate Plotly line chart below each ring
- Pros: Plotly is planned for ordinary charts ([ADR 0021](0021-react-vite-page-with-svg-radial-plots.md)).
- Cons: two renderers, no shared morph; Plotly cannot unwind a polar path into a line.

### C. Same SVG points, toggle with a ~1 s polar→Cartesian morph
- Pros: one data path; distinctive portfolio motion; accessibility via a real button and `aria-pressed`; reduced-motion can skip the tween.
- Cons: custom interpolation and hit-testing for both layouts.

## Decision
We will use **option C**. Each Kp tile keeps radial as the default. A small **Change Data View** button in the upper-left corner toggles that tile only. The same bins (time, Kp, G-scale color, fade) are drawn in both layouts. Animation lasts about one second with a fast-start, gentle-stop ease; `prefers-reduced-motion: reduce` jumps with no tween. Cartesian: time left→right from the lap’s 12 o’clock start, Kp up, same auto-scale (or fixed 0–9) as the ring, with a “now” marker.

## Consequences
- Easier: visitors can flip to a familiar chart without leaving the page; interviews can show custom SVG animation.
- Harder: hit-testing and labels must work in both geometries; Playwright needs a mobile tap check.
- Does not replace the table or CSV. Does not introduce Plotly for this path.

## How to explain this in an interview
"The default is still the radial Kp clock. Each tile has a Change Data View control that morphs the same SVG points into a time-on-x chart and back, about a second, like a rotary dial unwinding. Reduced-motion skips the tween. Both views share one bin list, so the numbers never disagree."

## Learn more
- [ADR 0021](0021-react-vite-page-with-svg-radial-plots.md) — SVG (not Plotly) for the Kp clocks
- MDN, [`prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- MDN, [`aria-pressed`](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-pressed)
