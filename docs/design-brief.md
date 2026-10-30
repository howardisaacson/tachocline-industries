# Tachocline Industries design brief

_Issue [#38](https://github.com/howardisaacson/tachocline-industries/issues/38). Built from [design_survey.md](research/design_survey.md) (ADR 0013) and the TI logo in [assets/brand/](../assets/brand/) (issue #22)._

This brief is the **working design system** for the public React site. Coding agents should follow it with [AGENTS.md](../AGENTS.md) and the Accepted ADRs. Do not copy SpaceX images, video, text, logos, or the licensed D-DIN font.

## 1. Brand signal
- **Mark:** magnetically active Sun with coronal loops (`assets/brand/ti-logo.svg`). Dark orange on black.
- **Wordmark:** “TACHOCLINE” in Barlow Bold, uppercase, wide tracking (~0.14em), beside the mark in the header.
- **First-viewport test:** after removing the nav, the page should still read as Tachocline (logo or hero Sun), not a generic dark dashboard.

## 2. Palette (from the logo)
Sampled from draft v1 / `ti-logo.svg`:

| Token | Hex | Use |
|---|---|---|
| `bg` | `#000000` | Page background |
| `fg` | `#F0F0FA` | Primary text (SpaceX-like tinted white) |
| `fg-dim` | `rgba(240,240,250,0.70)` | Secondary copy |
| `fg-mute` | `rgba(240,240,250,0.35)` | Borders, chip outlines, table rules |
| `accent` | `#D15D03` | Brand accent (buttons hover fill, focus, LIVE emphasis) |
| `accent-bright` | `#FB930E` | Highlights, G-scale gold end |
| `accent-deep` | `#9F2D01` / `#621201` | Chart storm fills, logo shadows |
| `surface` | `#232323` | Secondary button fill, panels |

**Rule:** black field + near-white type is the base (from the SpaceX survey). **TI adds a dark-orange accent from the logo**; SpaceX deliberately has no accent. That choice is [ADR 0025](decisions/0025-brand-accent-from-logo-orange.md) (Proposed).

Storm / NOAA G-scale on charts: quiet track stays cool/white; **Kp ≥ 5** uses gold→red drawn from `accent-bright` through `accent-deep`, not purple or neon.

## 3. Typography
| Role | Family | Size / weight | Notes |
|---|---|---|---|
| Display / H1 | Barlow Bold | ~50px mobile, ~100px desktop | Uppercase, ~0.95 line-height, slight tracking |
| Section H2 | Barlow Bold | ~1.5–3rem | Uppercase |
| Plot titles (H3) | Barlow Bold | ~1.4rem | Title case OK on plot cards |
| Body | Barlow Regular | 16–18px | Max measure ~40–42rem |
| Nav / labels | Barlow Bold | 13px | Uppercase, tracking ~0.09em |
| Data / tables / chips | Roboto Mono | 12px | Uppercase for table headers |

Load from Google Fonts (already in `web/index.html`). Never bundle D-DIN.

## 4. Grid and breakpoints
Follow [ADR 0012](decisions/0012-responsive-design-mobile-and-desktop.md):

| Name | Width | Layout |
|---|---|---|
| `mobile` | < 640 px | Single column; hero stacks; plots stack; day plot first |
| `tablet` | 640–1023 px | Still single-column plots; wider copy |
| `desktop` | ≥ 1024 px | Content max ~1400px; **three plot columns** (room for a fourth) |

- Page gutters: ~1.25rem; keep ~100px from the edge on large heroes where copy sits on imagery.
- Tap targets ≥ 44×44 px.
- No horizontal scroll at 320 px.
- Prefer `svh` for full-viewport heroes on desktop.

## 5. Chart style (radial Kp)
Per [ADR 0020](decisions/0020-radial-time-plots-for-space-weather.md) and [ADR 0021](decisions/0021-react-vite-page-with-svg-radial-plots.md):

- Angle = time (0 at 12 o’clock, clockwise). Radius = Kp (auto-scaled unless “Fixed 0–9” is on).
- Radar-sweep “now” head; older samples fade.
- SVG rings, not Plotly, for the clocks. Plotly remains for a later line-chart detail view.
- Each plot: hover/tap readout, table, CSV download.
- Layout: day first; one column < 640 px; row of three at ≥ 1024 px. The live page also reserves the **11-year** ring (GFZ since 1932); keep grid room for four tiles.

## 6. Imagery
| Asset | Use |
|---|---|
| `ti-logo.svg` | Header mark, favicon (with `favicon.ico`) |
| `ti-hero-wide.webp` | Desktop hero / tile backgrounds |
| `ti-hero-tall.webp` | Mobile hero |
| Dark gradient overlays | Transparent → black so type stays readable on the Sun |

Full-bleed heroes only; no inset cards for the hero image. Prefer WebP with PNG fallback.

## 7. Motion
- Staggered fade/slide for hero heading, lede, and CTA (~0.5–1s, short delays).
- LIVE dot pulse on the status chip.
- Button fill transition ~0.4–0.5s ease-out.
- Honor `prefers-reduced-motion: reduce` (disable non-essential motion).

## 8. Component list
| Component | Behavior |
|---|---|
| **Site header** | Fixed; logo mark + wordmark; primary nav; LIVE status chip; transparent with top gradient + light blur |
| **Status chip** | Outlined pill; `LIVE · Kp n · Gn`; optional hover panel later |
| **Hero** | Full-viewport on desktop; eyebrow, huge Kp readout, one sentence, one CTA |
| **Section** | One job, one H2, short supporting copy |
| **Plot card** | Title, note, SVG ring, CSV button, scrollable table |
| **Button** | ≥48px tall (small variant allowed for CSV); 4px radius; 1px `fg-mute` border; hover → accent or white fill |
| **About doc view** | Renders `docs/about/*.md` ([ADR 0024](decisions/0024-render-about-markdown-in-react.md)); header About link on every page |
| **Footer** | Compact, uppercase mono-ish credit line |
| **Spec table** | Roboto Mono, thin `fg-mute` row rules (orbit / flare lists) |

Suggested later tiles (survey mapping): Space Weather, Satellites, Data, Research, Workflow, About.

## 9. Accessibility
- Visible `:focus-visible` ring on interactive elements (`fg` on black).
- Decorative logo `alt=""` when wordmark text is present; home link has an accessible name.
- Charts always paired with a table or text alternative.
- Respect `prefers-color-scheme` only if a light theme is added later; **ship dark-first** to match the logo.

## 10. Out of scope (for now)
- Copying SpaceX’s hamburger overlay breakpoints; TI keeps ADR 0012.
- Light theme, purple accents, glassmorphism stacks, emoji.
- Replacing Grafana’s internal mission-control look (ADR 0007).

## Learn more
- [design_survey.md](research/design_survey.md)
- [assets/brand/README.md](../assets/brand/README.md)
- [ADR 0012](decisions/0012-responsive-design-mobile-and-desktop.md), [0013](decisions/0013-design-by-studying-existing-sites.md), [0020](decisions/0020-radial-time-plots-for-space-weather.md), [0025](decisions/0025-brand-accent-from-logo-orange.md)
