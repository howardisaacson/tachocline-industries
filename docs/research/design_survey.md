# Tachocline Industries: Design Survey
_Compiled 2026-10-20. URL status codes checked with curl that day. ✅ = 200 OK. ⚠️ = responded but blocked or redirected to bots (403/202/301). ❌ = 404 or no response. Award claims are marked **[verified]** only where the award page itself loaded. Claims marked **[reputation, unverified]** should be checked by hand before you quote them._

## A. Sites recognized for excellent design

### 1. Stripe: https://stripe.com ✅
- **Why it's acclaimed:** It has an Awwwards profile at https://www.awwwards.com/sites/stripe ✅ **[verified page exists]**, and it's cited all over the industry as the reference for developer-focused marketing sites.
- **Patterns:** an animated gradient "mesh" hero; a tight 12-column grid; a custom sans typeface (Söhne); code samples placed next to marketing copy; diagonal section breaks; menus that open as cards on hover, which become an accordion drawer on mobile.
- **What TI could borrow:** an animated gradient hero shaped like solar plasma; code snippets shown beside the charts ("here's the query behind this"), which is good for showing engineering skill.

### 2. Linear: https://linear.app ✅
- **Why it's acclaimed:** It's widely credited with starting the "Linear look": a dark theme, glowing accents and very sharp typography. **[reputation, unverified]**. The Awwwards slug I guessed returned 404, so I have no award to cite.
- **Patterns:** a near-black background; one accent color; the Inter typeface with tight letter spacing; product screenshots with a subtle 3D tilt; elements that reveal as you scroll; a very fast, minimal nav.
- **What TI could borrow:** a dark "observatory" theme with a single solar-orange accent; restrained motion.

### 3. Apple: https://www.apple.com ✅
- **Why it's acclaimed:** It has a long run of Webby honors and a reputation for product storytelling **[reputation, unverified; Webby winners index https://www.webbyawards.com/winners/ ✅ can be searched]**.
- **Patterns:** scroll-driven "sticky" storytelling sections; huge headlines in SF Pro; lots of white or black space; images that swap per breakpoint (art direction by screen size); a global nav that collapses to a hamburger menu.
- **What TI could borrow:** a scroll-told story of a solar storm ("flare → CME → Kp spike → satellite drag").

### 4. Vercel: https://vercel.com ✅
- **Why it's acclaimed:** Its design system (Geist) is respected by developers **[reputation, unverified]**.
- **Patterns:** a monochrome palette; the Geist Sans and Geist Mono fonts; grid-line backgrounds; live deploy and status widgets; excellent dark mode.
- **What TI could borrow:** mono fonts for data readouts, and a "status page" layout for current space weather.

### 5. Figma: https://www.figma.com ✅
- **Why it's acclaimed:** Webby and Awwwards recognition is commonly cited **[reputation, unverified]**.
- **Patterns:** bright, playful color blocks; interactive product demos embedded in the page; a strong system of reusable components.
- **What TI could borrow:** interactive demos instead of static images.

Award directories for further checking: Awwwards https://www.awwwards.com/sites/stripe ✅, CSS Design Awards https://www.cssdesignawards.com ⚠️(202), Webby winners https://winners.webbyawards.com ✅.

## B. Highly rated science and science-data sites

### 1. NASA's Eyes: https://eyes.nasa.gov ✅
- **Why it's acclaimed:** NASA web properties have won many Webby awards; Eyes on the Solar System is often featured **[reputation, unverified for a specific award]**.
- **Patterns:** a full-screen WebGL 3D scene; a timeline scrubber; search for spacecraft; minimal overlay UI. It is heavy on mobile but works.
- **What TI could borrow:** a 3D Earth with satellite orbits and a time scrubber that is synced to the Kp chart.

### 2. NOAA SWPC: https://www.swpc.noaa.gov ✅
- **Why it's acclaimed:** It is the official US space-weather authority and the most-used dashboard for the field. Its design is dated, but its information structure is the domain standard.
- **Patterns:** a dashboard of tiles; the 1–5 G/S/R scales with color codes; image loops; "Products" pages (for example https://www.swpc.noaa.gov/products/planetary-k-index ✅).
- **What TI could borrow:** NOAA's G/S/R scale vocabulary and colors. TI can offer a cleaner, mobile-first version of this dashboard.

### 3. Our World in Data: https://ourworldindata.org ✅
- **Why it's acclaimed:** It is widely praised by data-visualization practitioners and has received Webby recognition **[reputation, unverified]**. It is open source (the Grapher tool).
- **Patterns:** a chart/map/table toggle on every chart; download CSV and embed buttons; a source note under every chart; clear, readable serif text.
- **What TI could borrow:** "download this data" and "source" links on every plot. This is a strong signal of data-engineering skill.

### 4. Helioviewer: https://helioviewer.org ✅
- **Why it's acclaimed:** It is the NASA/ESA-funded standard tool for browsing solar imagery from SDO and SOHO. It is recognized in the science community, not through design awards.
- **Patterns:** a layered image viewer; a date picker; a public API; movie export.
- **What TI could borrow:** embedding or calling the Helioviewer API to show the Sun on the day of each storm.

### 5. Quanta Magazine: https://www.quantamagazine.org ✅
- **Why it's acclaimed:** It is known for excellent science explainers and interactives **[reputation, unverified for a specific award]**.
- **Patterns:** an editorial layout with large illustrations; generous serif body text; inline interactives.
- **What TI could borrow:** the editorial "explainer" format for the physics pages.

Also checked: ESA https://www.esa.int ✅, Nature https://www.nature.com ✅.

## Comparison table
| Site | Theme | Typography | Data viz | Navigation | Mobile | Borrow for TI |
|---|---|---|---|---|---|---|
| Stripe | Light + gradient | Custom sans | Code + diagrams | Card menus | Drawer | Gradient hero, code next to charts |
| Linear | Dark | Inter, tight | Screenshots | Minimal | Clean stacks | Dark theme, single accent |
| Apple | B/W | SF Pro, huge | Scroll story | Global bar | Art-directed | Storm scrollytelling |
| Vercel | Mono | Geist + Mono | Live widgets | Top bar | Good | Status-page layout |
| Figma | Bright | Custom | Interactive demos | Mega menu | Good | Interactive demos |
| NASA Eyes | Dark 3D | Sans | WebGL 3D | Overlay | Heavy | 3D orbits + time scrubber |
| NOAA SWPC | Gov | Default | Tiles, loops | Dense | Weak | G/S/R scales |
| OWID | Light | Serif + sans | Chart/map/table | Search | Excellent | Download/source on each chart |
| Helioviewer | Dark | Sans | Image layers | Tool UI | Limited | Solar imagery API |
| Quanta | Light editorial | Serif | Interactives | Simple | Excellent | Explainer pages |

## Three design directions for TI
1. **"Mission Control" (dark dashboard, influenced by Linear, Vercel and SWPC).** Near-black background, a solar-orange accent and mono data readouts.
   - Desktop: a 3-column grid of live tiles (Kp, F10.7, X-ray flux, satellites tracked).
   - Mobile: tiles stack into one column with swipeable mini-charts, and the most urgent alert is pinned at the top.
2. **"Storm Story" (scrollytelling, influenced by Apple and Quanta).** One long narrative following the May 2024 storm from the Sun to satellite drag to the power grid.
   - Desktop: a sticky chart on the left while text scrolls on the right.
   - Mobile: the chart sits full-width with text cards over it, and images are lighter.
3. **"Open Data Lab" (influenced by OWID and Stripe).** Each chart is shown with its source, a CSV/API download, and the Python/SQL snippet that produced it.
   - Desktop: the chart and code side by side.
   - Mobile: chart/code/data tabs.
   - This shows off pipeline skills the most clearly.
