# Tachocline Industries: Design Survey

_Updated 2026-10-27 for issue [#37](https://github.com/howardisaacson/tachocline-industries/issues/37). Decision: the TI frontend will resemble the structure and visual language of [spacex.com](https://www.spacex.com). The earlier list of design-award sites and all award claims were removed. Space and science links are kept below as references. The links under "Space and science references" loaded when checked on 2026-10-26, except where a note says otherwise._

## Part 1. SpaceX design brief (for Cursor and other coding agents)

**How to use this brief:** build TI's frontend (React, per ADR 0007) so its layout and feel follow spacex.com. Follow the patterns. Do **not** copy SpaceX's images, video, text, logos or the licensed D-DIN font. Use TI's own assets and free fonts. See AGENTS.md for repo rules, and ADR 0012 for the responsive breakpoints (640 and 1024 px) already agreed. Where this brief gives SpaceX's breakpoints, treat them as reference only and keep TI's.

**Confidence note:** spacex.com is a JavaScript single-page app, so its HTML is an empty shell. This analysis was read from its CSS, JS bundles, HTTP headers and public CMS JSON, **not from a rendered screenshot**. Scroll behavior, video use per section, and sticky or hide-on-scroll header behavior were not confirmed. Check the live site in a browser before relying on those details.

### Visual language
- Black everywhere. SpaceX sets `background-color: #000` with near-white text and has **no accent color**.
- Palette is one tinted white at different opacities: `#f0f0fa` (rgba 240,240,250) at 100%, then 90/80/70/60/50/35/30/15/10% steps. Row dividers and button borders use white at 25% to 35% opacity. Secondary button fill is `#232323`.
- Fonts SpaceX uses: D-DIN (body), D-DIN Bold (h1, h2), Roboto Mono (tables, countdowns, small labels). D-DIN is licensed. **For TI use Barlow** (free, DIN-like, on Google Fonts) and **Roboto Mono** (free).
- Type: headings are UPPERCASE, bold, tight line height (about 95%) with a little letter spacing. h1 and h2 about 3rem. The big hero heading is about 100px on desktop and 50px on mobile. Nav links are 13px, bold, uppercase, wide tracking (about 0.09em). Small mono labels are 12px uppercase.
- Imagery: full-bleed photo or video behind text, with dark gradient overlays (transparent to black at the bottom or sides) so text stays readable. Separate desktop and mobile images exist for each hero.
- Buttons: 48px tall, 4px corner radius, 1px border at 35% white, transparent or near-black fill. On hover the button fills white and the text turns black, with a smooth ease-out transition of about 0.4 to 0.5 seconds.
- Header: fixed over the content, transparent with a top-down dark gradient and a light background blur.

### Page and navigation structure
- Header: logo on the left, nav links, and a live status chip on the right (SpaceX shows the next launch). Hovering a nav item opens a dropdown.
- SpaceX's main nav: Vehicles, Human Spaceflight, Starlink, Company, and others; routes include `/launches`, `/vehicles/*`, `/humanspaceflight`, `/updates`, `/careers`, `/mission`.
- Footer: small, dark, with a social icon button, a few legal and careers links, and copyright.
- **Suggested TI mapping** (suggestion, not from SpaceX): Space Weather (live dashboard), Satellites (orbit and decay data), Data (pipeline, sources, downloads), Research, Workflow (data science workflow, ADRs), About. Keep the "About this page" link on every section (ADR 0009).

### Layout patterns
- The homepage is a stack of full-viewport tiles. Each tile is a background image or video with **one heading, one sentence and one call-to-action button** (SpaceX uses "EXPLORE").
- Text is placed in fixed slots on the tile: center, left-middle, left-bottom, right-middle and so on. Text blocks are about 520px wide at most, about 100px from the screen edge, and the content column maxes out near 1400px.
- SpaceX tiles are at least the full screen height (`max(100svh, 941px)`). On mobile the height becomes automatic and left or right text blocks become full-width.
- Launch pages use tables in Roboto Mono, uppercase, with thin white (25%) lines between rows, plus filter dropdowns and a pager.
- Status chip: a small outlined pill that shows a blinking LIVE dot or a countdown. Digits roll like an odometer. Hovering opens a small blurred panel of cards.
- Other components seen: a horizontal step timeline with dots, stats tiles, and carousels.

### Motion
- Heading, subheading and button fade or slide in one after another on load (about 0.5 to 1 second each, with short delays).
- Background video and carousels exist. Parallax is only confirmed on one SpaceX tracker page, so don't assume it for the homepage.
- Keep motion restrained, and honor `prefers-reduced-motion`.

### Responsive behavior
- SpaceX's CSS breakpoints are 1500, 1350, 1279 and 961px. Below 1279px the nav becomes a full-screen black overlay opened with a hamburger button. Below 961px sections stack, the hero heading shrinks, and the footer becomes a column. The launch chip becomes a plain list on small screens.
- TI rule (H5): every page must be specified and tested for both mobile and desktop browsers.

### Suggested TI components (suggestions, built from the patterns above)
1. **Hero:** full-screen dark image of the Sun with a very large live readout such as the current Kp index and G-scale, one "EXPLORE" button.
2. **Status chip in the header:** "LIVE · Kp 4 · G1" with a blinking dot. The hover panel shows solar wind speed, X-ray flux class and the next expected event.
3. **Spec tables:** Roboto Mono, uppercase, thin dividers, for satellite orbit data, flare lists and data-source details.
4. **Tile stack on the homepage:** one tile each for Space Weather, Satellite Drag Watch, Data Pipeline, Research, and Data Science Workflow.
5. **Dark gradient overlays and a fixed transparent header** as above.
6. **Source and download links** under every chart, so readers can see where the data came from.

### Main data visual: radial Kp plots ([ADR 0027](../decisions/0027-eleven-year-kp-ring-with-gfz.md), supersedes [0020](../decisions/0020-radial-time-plots-for-space-weather.md))
SpaceWeatherLive already plots activity with time on the x-axis and the value on the y-axis, so TI will not copy that. The main visual is a set of **radial plots** for **a day, a month, a year, and 11 years**. The 11-year ring uses **GFZ definitive Kp since 1932** (no longer deferred).
- Angle is time. Zero is at the top (12 o'clock) and time runs clockwise.
- Distance from the center is the activity indicator. The first indicator is the **Kp index**.
- The radius auto-scales: the largest value in the window sits at the circle's edge. The scale rings and the maximum are always labeled.
- Radar-sweep behavior: a bright "now" head moves clockwise, older data fades, and the sweep overwrites older data naturally. Each lap starts on a fixed UTC boundary (midnight, the 1st of the month, 1 January; the 11-year lap is measured from 1 January 1932).
- Day ring: SWPC 1-minute estimated Kp. Longer rings: GFZ 3-hour Kp (daily max on year and 11-year).
- Layout: up to four plots in a row on wide screens (1024 px and up), one column on mobile (below 640 px), day plot first. Each plot has a tap or hover readout, a data table, a CSV download and an "About this page" link.

On the SpaceX-style tiles this works as the hero: the radial plots sit over the dark background, and the header status chip shows the live Kp value.

### Tech stack note
spacex.com is built with Angular, served through Cloudflare, with a Strapi CMS for content. TI uses React (ADR 0007), so borrow the patterns and not the stack. Never reuse SpaceX's font files, images or video.

### SpaceX links
- Site: <https://www.spacex.com>
- Homepage content feed (public CMS JSON): <https://content.spacex.com/api/spacex-website/homepage-tiles>
- Third-party write-ups of its design system (these disagree with the CSS in places, for example about button shape and overlays, so treat them as secondary):
  - <https://design.fish/design-md/spacex-com>
  - <https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/spacex/DESIGN.md>
  - <https://github.com/beefiker/superloopy/blob/main/skills/superloopy-frontend/references/design/spacex.md>
  - <https://opendesigner.io/design-systems/spacex>
  - <https://www.shadcn.io/design/spacex>
- Related space product sites worth viewing next to it: <https://starlink.com/> and its coverage map <https://starlink.com/map>.
- Free fonts for TI: [Barlow](https://fonts.google.com/specimen/Barlow) and [Roboto Mono](https://fonts.google.com/specimen/Roboto+Mono).

## Part 2. Space and science references

These are worth viewing for data presentation and for data sources. No award claims are made for any of them.

### Space weather and solar
- NOAA SWPC: <https://www.swpc.noaa.gov> (official US space-weather source; its G/S/R scales are the domain vocabulary; example product page <https://www.swpc.noaa.gov/products/planetary-k-index>)
- SpaceWeatherLive: <https://www.spaceweatherlive.com/> (live solar and aurora data; aurora oval page <https://www.spaceweatherlive.com/en/auroral-activity/auroral-oval.html>)
- ESA Space Weather portal: <https://swe.ssa.esa.int/>
- Helioviewer: <https://helioviewer.org> (solar imagery viewer with a public API; it redirects to a NASA-hosted address)

### Satellites and orbits
- Stuff in Space (maintained fork): <https://ajmas.github.io/StuffInSpace/> and source <https://github.com/ajmas/StuffInSpace> (3D view of orbiting objects from Space-Track data; the original stuffin.space did not resolve when checked)
- CelesTrak: <https://celestrak.org/> (orbital elements <https://celestrak.org/NORAD/elements/>, conjunction reports <https://celestrak.org/SOCRATES/>)
- Space-Track: <https://www.space-track.org/> (official catalog and API; only the login page was confirmed to load)
- Heavens-Above: <https://www.heavens-above.com/> (satellite pass tracking; very dense layout, so useful as a "what to avoid" example)

### Data visualization and storytelling
- NASA Eyes: <https://eyes.nasa.gov> (real-time 3D with a time scrubber)
- NASA Worldview: <https://worldview.earthdata.nasa.gov/> (layered data with a time slider)
- Our World in Data: <https://ourworldindata.org> (source and CSV download on every chart)
- The Pudding: <https://pudding.cool/> (data storytelling)
- Quanta Magazine: <https://www.quantamagazine.org> (editorial science explainers)
- Grafana Play: <https://play.grafana.org/> (live demo dashboards) and the dashboard gallery <https://grafana.com/grafana/dashboards/>
- Planet Explorer: <https://www.planet.com/explorer/> (satellite imagery browser)
- Information is Beautiful Awards showcase: <https://www.informationisbeautifulawards.com/> (gallery of data visualizations; used here only as a source of examples)

_Not checked or not loading as of 2026-10-26: Observable (<https://observablehq.com/>, returned a bot-check error) and the New York Times graphics page (403)._
