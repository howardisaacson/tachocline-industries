# 0034. Draw the public perigee chart in SVG

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

## Context

Issue #109 asks for the Grafana **Perigee altitude** panel on the public site: five satellites, kilometers, last 7 days. [ADR 0021](0021-react-vite-page-with-svg-radial-plots.md) drew the Kp rings in SVG and left Plotly.js as the plan for a later line chart. This is that line chart. The points come from `GET /api/v1/satellite-perigee`, which rejects a window longer than 7 days.

## Options considered

### A. Plotly.js line chart

- Pros: hover and zoom come with the library. ADR 0021 already named it for this kind of chart.
- Cons: a large dependency for one chart. The axis math is inside the library while the rest of the site is hand-drawn SVG.

### B. SVG in the page, sized in CSS pixels

- Pros: the same approach as the Kp rings. A higher kilometer is a smaller `y`, which is a few lines Howard can explain. Sizing the SVG to the container keeps the labels at 12 px on a phone. A scaled viewBox would shrink them.
- Cons: zoom and a brush are our code if we want them later.

### C. Embed the Grafana panel

- Pros: the picture already exists.
- Cons: Grafana is the internal dashboard. The public site is supposed to read FastAPI only ([ADR 0007](0007-grafana-now-react-later-for-frontend.md)).

## Decision

We will use **option B**.

`/satellites` requests the last 7 days from `GET /api/v1/satellite-perigee` and draws ISS (25544), Landsat 8 (39084), Landsat 9 (49260), HST (20580), and Swift (28485). Landsat 9 is dashed because the two Landsats share an altitude. The nav link is **Satellite Tracking**. Under the chart, each satellite links to an N2YO tracking page and a NASA homepage. Those links are not the data source. CelesTrak is.

This supersedes the Plotly line-chart plan in ADR 0021 for this chart. The radial plots stay SVG. ADR 0021's decision is otherwise unchanged.

## Consequences

- Easier: no new frontend dependency. The chart and the Grafana panel show the same five series.
- Harder: a longer public history is still an API change. Rows are tagged by poller, and the public routes return `celestrak` only ([ADR 0035](0035-what-may-be-shown-publicly.md)).

## How to explain this in an interview

"The public chart is an SVG polyline. Time is x, perigee in kilometers is y, and a higher altitude is closer to the top. The browser asks FastAPI for seven days because that route will not serve a longer window. I skipped Plotly so this one chart would not add a large library."

## Learn more

- [ADR 0021](0021-react-vite-page-with-svg-radial-plots.md) (SVG for the Kp rings; Plotly was the old line-chart plan)
- MDN, [SVG polyline](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/polyline)
- React, [`useEffect`](https://react.dev/reference/react/useEffect) (measure the container, then draw)
