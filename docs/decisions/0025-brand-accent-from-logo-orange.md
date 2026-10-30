# 0025. Use the logo’s dark orange as the brand accent on black

- **Status:** Proposed
- **Date:** 2026-10-29
- **Deciders:** Howard Isaacson

## Context
[ADR 0013](0013-design-by-studying-existing-sites.md) and the [design survey](../research/design_survey.md) aim the public site at spacex.com’s structure: black background, near-white type, Barlow + Roboto Mono. SpaceX’s CSS has **no accent color**. The TI logo (issue #22) is a magnetically active Sun in dark orange (`#D15D03`, `#FB930E`, `#9F2D01`) on black. The [design brief](../design-brief.md) (issue #38) needs a clear rule: stay accent-free like SpaceX, or adopt the logo orange.

## Options considered
### A. No accent (match SpaceX exactly)
- Pros: closest to the survey; simplest palette.
- Cons: the logo’s orange never appears in UI chrome; the site can feel generic dark UI once the mark is small in the header.
### B. Dark orange accent from the logo
- Pros: ties chrome, focus rings, and storm highlights to the brand mark; still reads as “space black,” not a colorful dashboard.
- Cons: diverges from SpaceX’s accent-free system; accent must stay sparse or the page gets noisy.
### C. Separate chart-only orange, accent-free chrome
- Pros: charts can use solar color without changing buttons/nav.
- Cons: two rules to remember; header/CTA stay disconnected from the mark.

## Decision
We will use **option B**. TI’s base remains black + `#F0F0FA` type. The brand accent is the logo orange (`#D15D03` primary, `#FB930E` bright, `#621201`/`#9F2D01` deep). Use it sparingly: logo, LIVE emphasis, focus, hover fills, and Kp ≥ 5 chart segments. Do not flood backgrounds with orange.

## Consequences
- Easier: one story from favicon to charts; the design brief has concrete tokens.
- Harder: every new component must ask “does this need accent?”; reviewers should reject purple/neon accents that fight the Sun.
- Grafana can keep its own theme; this ADR is for the public React site.

## How to explain this in an interview
"We studied SpaceX’s black-and-white system, but our mark is a dark-orange Sun, so we added that orange as a scarce accent instead of staying accent-free. The page stays mostly black and white; orange shows up in the logo, focus states, and storm-level Kp so the brand and the science use the same color language."

## Learn more
- [design-brief.md](../design-brief.md)
- [assets/brand/ti-logo.svg](../../assets/brand/ti-logo.svg)
- Google Fonts, [Barlow](https://fonts.google.com/specimen/Barlow)
