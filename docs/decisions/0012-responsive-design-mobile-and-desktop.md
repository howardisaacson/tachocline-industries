# 0012. Responsive design: every page specified for mobile and desktop

- **Status:** Proposed
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
Howard wants every page to have **mobile and web-browser specs**. Many recruiters first open a portfolio link on a phone. Data-heavy pages (time-series charts, maps) are where mobile usually breaks: tiny unreadable charts, sideways scrolling, hover-only tooltips. Interviewers for frontend or full-stack roles may ask how the UI adapts.

Key terms:
- **Responsive design:** one site whose layout adapts to screen width using flexible grids and CSS **media queries**.
- **Mobile-first:** write base styles for small screens, then add styles for larger ones (`@media (min-width: …)`).
- **Breakpoint:** a width where the layout changes.
- **Viewport meta tag:** tells phones to use the device width instead of pretending to be a desktop.

## Options considered
### A. Desktop-first, fix mobile later
- Pros: faster for chart-heavy pages initially.
- Cons: retrofitting is painful; mobile ends up second-rate.
### B. Separate mobile site
- Pros: fully tailored.
- Cons: two codebases; outdated practice.
### C. Responsive, mobile-first, with written per-page specs and tests
- Pros: one codebase; modern standard; forces prioritising the most important content; testable.
- Cons: more design thinking per page; charts need deliberate mobile variants.

## Decision
Adopt **mobile-first responsive design** with these breakpoints, aligned to Tailwind CSS defaults in case we use it:

| Name | Min width | Test widths |
|---|---|---|
| mobile | 0 | 320, 375, 390 px |
| tablet | 640 px | 768 px |
| desktop | 1024 px | 1280, 1440 px |

Every page spec (and its About page) includes a short **"Mobile / Desktop" section** covering layout, which charts are shown or simplified, interactions (tap vs hover), and image sizes. Rules: no horizontal scroll at 320 px; tap targets ≥ 44 px; tooltips also work by tap; charts get mobile variants (fewer series, larger fonts, stacked panels); accessible contrast (WCAG AA); support `prefers-reduced-motion`.

**Testing:** browser DevTools device mode during development; **Playwright** viewport tests (mobile + desktop screenshots) in CI once `web/` exists; a real-phone check before release. Grafana (internal) is checked in a narrow window, with limitations noted.

## Consequences
- Easier: a credible portfolio on any device; mobile becomes a clear interview talking point.
- Harder: more work per page, especially charts and maps.
- Adds Playwright to the toolchain (Phase 3).

## How to explain this in an interview
"Every page was designed mobile-first with three breakpoints, and each page spec says what changes between phone and desktop, for example stacking chart panels and switching hover tooltips to tap. Playwright tests render each page at phone and desktop sizes in CI so layout regressions get caught automatically."

## Learn more
- MDN, [Responsive design](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/CSS_layout/Responsive_Design); web.dev, [Responsive web design basics](https://web.dev/articles/responsive-web-design-basics)
- Chrome DevTools, [Device mode](https://developer.chrome.com/docs/devtools/device-mode); Playwright, [Emulation](https://playwright.dev/docs/emulation)
- Tailwind CSS, [Responsive design](https://tailwindcss.com/docs/responsive-design); W3C, [WCAG](https://www.w3.org/WAI/standards-guidelines/wcag/)
