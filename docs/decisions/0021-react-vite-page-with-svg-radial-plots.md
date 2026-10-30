# 0021. Serve the first public page with Vite, and draw the radial plots in SVG

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Howard Isaacson

## Context
[ADR 0007](0007-grafana-now-react-later-for-frontend.md) keeps Grafana as internal mission control and says the public site is React, reading only from FastAPI. It also says the move to React needs its own decision for the build tool, hosting, and routing. [ADR 0020](0020-radial-time-plots-for-space-weather.md) makes the first picture three radial Kp plots, with a trace that fades as it ages and a bright head at now. [ADR 0014](0014-when-to-use-more-than-one-docker-container.md) already reserved a `web` container: a Node build that serves static files.

Plotly's `scatterpolar` can put zero at the top and run clockwise. One Plotly line has one color. Fading each segment by age means many traces, or a custom drawing. ADR 0020 asked for a short spike before building. This ADR records that spike.

## Options considered
### A. Plotly.js polar traces for the three rings
- Pros: matches the example named in ADR 0007; hover and zoom come with the library.
- Cons: a fading stroke is awkward; the bundle is large for three clocks; the geometry is hidden inside the library while Howard is learning it.
### B. SVG drawn by React
- Pros: each segment can have its own opacity and G-scale color; the angle and radius are a few lines of math Howard can explain; the page stays small.
- Cons: hover, axes, and later line charts are our code. Plotly is still the better tool when a normal time-on-x chart is added.
### C. Vite + nginx, versus webpack or serving the build from FastAPI
- Pros of Vite: the current default for a React app, a dev server with a proxy, and a static `dist/` folder. nginx in its own container matches ADR 0014 and can proxy `/api` so the browser is same-origin. The API then does not need a CORS header.
- Cons: another image to build. Serving the files from FastAPI would avoid that image and would couple a frontend release to an API restart.

## Decision
We will use **option B and option C**. The first public page is a Vite + React app in `web/`. Compose service `web` builds it and nginx serves it on port 80, published on `127.0.0.1`. nginx proxies `/api` to the `api` service. The radial plots are SVG. Plotly.js remains the plan for a later line-chart detail view, which ADR 0020 postponed.

The page is one screen: a live Kp readout and the day, month, and year rings, each with a table and a CSV download. There is no client-side router yet. A second page can add one.

`GET /api/kp-3h` may cover 400 days and 3300 rows so the year ring is one request. Minute routes stay at 7 days and 2000 rows.

## Consequences
- Easier: the fade and the empty arc are visible; the browser never talks to Postgres; local dev (`npm run dev`) and Compose use the same `/api` paths.
- Harder: two ways to draw a chart until a line chart needs Plotly; the year ring is only as full as the rows the poller has stored.
- ADR 0020 stays the design rule. This ADR is how that picture is built.

## How to explain this in an interview
"The public page is a static React build behind nginx. nginx proxies `/api` to FastAPI, so the browser has one origin and the API does not need CORS. I drew the Kp clocks in SVG instead of Plotly because each segment has to fade with age and change color at Kp 5. Plotly is still the plan when I add an ordinary line chart."

## Learn more
- Vite, [Getting Started](https://vite.dev/guide/)
- React, [Learn React](https://react.dev/learn)
- nginx, [`ngx_http_proxy_module`](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- MDN, [SVG as an image](https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorials/SVG_from_scratch/SVG_and_CSS)
