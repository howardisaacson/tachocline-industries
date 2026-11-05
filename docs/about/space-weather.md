# About this page: Space weather

> **Last reviewed:** 2026-11-05 · **Owner:** Howard Isaacson
>
> Written from [the About template](../about-this-page-template.md) ([ADR 0009](../decisions/0009-about-this-page-for-every-section.md)).

The page is the public site at `http://127.0.0.1:8080` (host port `WEB_PORT`). The site renders **this markdown file** at `/about/space-weather` ([ADR 0024](../decisions/0024-render-about-markdown-in-react.md)); the header **About** link opens that route. There is no second copy of this prose in React. A license note under the markdown is shared by every About route. Grafana still has the time-on-x charts. This page does not replace them.

## 1. Purpose
Shows how disturbed Earth's magnetic field is, at three zoom levels, without copying the usual "time on the x-axis" chart. The page is for a visitor who wants the current Kp and for an interviewer asking why the picture is a clock. The numbers are real-time SWPC estimates. They are not the definitive GFZ Kp and they are not a forecast. Under the rings, the page also shows 7 days of Sun-as-a-star radial velocity from NEID and EXPRES.

## 2. What you're seeing
The hero is the latest 1-minute `estimated_kp`. Below G1 means Kp is under 5. G1 and above follow [NOAA's scale](https://www.swpc.noaa.gov/noaa-scales-explanation).

Each ring is one lap. Twelve o'clock is the start of that lap. Time runs clockwise. Distance from the center is Kp. The largest value in the window sits on the outer ring unless **Fixed 0–9 scale** is on. A white dot on the rim is now. Older samples are fainter. Gold through red is Kp 5 and above, so a quiet day that fills its own ring does not look like a storm. An empty arc is a time Tachocline has not stored. It is not a zero. Move the pointer over the ring (or the now head) to update the centered readout under the plot with UTC time and Kp.

- **One day:** 1-minute estimated Kp averaged into 10-minute bins. The lap starts at midnight UTC. About 144 bins when the day is full.
- **30 days:** GFZ 3-hour Kp. The lap starts on the 1st of the month, UTC. The values are the latest 30 days.
- **One year:** the daily maximum of GFZ 3-hour Kp. The lap starts on 1 January UTC.
- **11 years:** the daily maximum of GFZ Kp. The lap is 11 × 365 days measured from 1 January 1932 ([ADR 0027](../decisions/0027-eleven-year-kp-ring-with-gfz.md); no longer deferred). A recent row can still be a nowcast. The next daily file replaces it.

Under each ring, one sentence compares that stretch with earlier stretches of the same length ([ADR 0036](../decisions/0036-plain-language-kp-sentences.md)). **How is this worked out?** opens the method below.

### How the sentence is worked out

The day sentence uses today's mean of SWPC 1-minute estimated Kp, set against the mean of each of the previous 7 UTC days. The other three sentences use GFZ 3-hour Kp. "The last 30 days" is compared with the 12 blocks of 30 days before it. "The last 365 days" is compared with each complete calendar year since 1932 that ended before that window. "The last 11 years" is the last 11 × 365 days, compared with earlier blocks of that length back to 1 January 1932. Those blocks are the ring's length. They are not solar-cycle minima.

The label is how far the current mean sits from the mean of those baseline windows, using the population standard deviation. More than 1 SD out is "well below" or "well above". Between 0.5 and 1 SD is "below" or "above". Inside 0.5 SD is "about average". If the spread is zero, the label is about average, above, or below, and never "well". A finished UTC day needs at least 720 one-minute samples before it can be one of the seven baseline days. Today can be described after 60 samples, and the sentence then says "so far". A GFZ window counts only when at least half its days have 4 of the 8 three-hour slots. The mean still uses every stored slot. If that coverage is missing, the sentence says the record is too short and does not pick a label.

Numbers in the sentence are those means and peaks rounded to two decimal places. The year sentence also gives the percent of earlier complete years whose mean is strictly lower, rounded to the nearest whole percent. A peak of Kp 5 or more adds the NOAA G-scale and the UTC time of that peak. The route is `GET /api/v1/kp-interpretation`. It runs when the page loads. It is not a forecast and not a model.

### Sun-as-a-star radial velocity

Under the rings, one time-on-x chart draws the last 7 days of solar radial velocity from NEID and EXPRES ([ADR 0037](../decisions/0037-solar-rv-scalars-from-neid-and-expres.md)). The unit is meters per second. Each point is one exposure of the whole solar disk, not a spectrum and not a Kp. A line joins exposures that are 30 minutes apart or closer. A longer hole stays open. An archive uncertainty of 9999, or a velocity outside ±5000 m/s, is stored as a gap so a failed reduction cannot set the scale. An empty EXPRES series means the archive has not published an EXPRES day inside the window. Checked 2026-11-05, the newest EXPRES Level 2 row was 2026-04-25. The route is `GET /api/v1/solar-rv`. The caption links to the [NExScI Solar RV Archive](https://neid.ipac.caltech.edu/search_solar.php).

**Change Data View** (upper-left on each tile, faint until hover or focus) unwinds that ring into a time-on-x chart and back, about one second, like a rotary dial ([ADR 0029](../decisions/0029-radial-cartesian-unwind-toggle.md)). Each tile toggles on its own. Both layouts draw the same bins; only the geometry changes. `prefers-reduced-motion` skips the tween. The blurb above each plot links to the source’s main site under the source name (**NOAA SWPC** or **GFZ**). **Download CSV** saves `time_utc`, `kp`, and `g_scale` for the bins on that ring. Move the pointer over the plot to update the readout. The header chip repeats the latest Kp.

## 3. Data source & cadence
| Item | Value |
|---|---|
| Provider | [NOAA SWPC](https://www.swpc.noaa.gov/products/planetary-k-index), real-time estimated Kp. The page reads it from our API, not from SWPC directly. |
| Satellite(s) / instrument(s) | Ground magnetometers. The 3-hour product names Sitka, Meanook, Ottawa, Fredericksburg, Hartland, Wingst, Niemegk, and Canberra. |
| Endpoint | `GET /api/v1/kp-1m` for the day ring and the hero. `GET /api/v1/kp-gfz` for the 30-day, year, and 11-year rings. `GET /api/v1/kp-interpretation` for the sentence under each ring. `GET /api/v1/solar-rv` for the velocity chart. |
| Format / access | JSON over HTTP, no auth, same origin. The `web` container proxies `/api` to the API container. |
| Upstream update cadence | 1-minute estimated Kp and 3-hour estimated Kp ([data_sources.md](../research/data_sources.md)). |
| Our polling cadence | `SWPC_POLL_MINUTES` (5 in `.env.example`). |
| End-to-end latency | Not measured. A row is visible after the next poll and a reload of the page. The page does not refresh itself. |
| Processing level | Real-time. The API body says `processing_level: real-time`. |
| History we keep | The day call asks for 24 hours of SWPC 1-minute Kp (limit 2000). The longer rings ask for 11 × 365 days of GFZ Kp (limit 40000). GFZ publishes the series since 1932. |

## 4. Data flow
```mermaid
flowchart LR
    MAG["Ground magnetometers"] --> SWPC["NOAA SWPC Kp JSON"]
    SWPC -->|"HTTPS"| POLL["Python poller"]
    POLL --> DB[("PostgreSQL + TimescaleDB<br/>planetary_kp_1m, planetary_kp_3h")]
    DB --> API["FastAPI"]
    API --> WEB["nginx proxies /api<br/>React page draws SVG rings"]
```
The poller stores the rows. The page asks the API for them. FastAPI checks the window, then runs a SELECT as the read-only role. The browser draws the rings. It never opens Postgres.

## 5. Tech used and why
| Layer | Technology | Why (one line) | Decision |
|---|---|---|---|
| Page | React, built with Vite | Components for the hero, the rings, CSV download, and About. | [ADR 0007](../decisions/0007-grafana-now-react-later-for-frontend.md), [ADR 0021](../decisions/0021-react-vite-page-with-svg-radial-plots.md) |
| Picture | SVG | Each segment can fade and take a G-scale color; polar↔Cartesian morph stays in SVG. | [ADR 0020](../decisions/0020-radial-time-plots-for-space-weather.md), [ADR 0029](../decisions/0029-radial-cartesian-unwind-toggle.md) |
| API | FastAPI | The page reads Kp through GET routes. | [ADR 0006](../decisions/0006-fastapi-for-backend-api.md) |
| Runtime | nginx in the `web` container | Static files, and `/api` stays on the page's origin. | [ADR 0014](../decisions/0014-when-to-use-more-than-one-docker-container.md) |

Key code: [`web/src/App.jsx`](../../web/src/App.jsx), [`web/src/kp.js`](../../web/src/kp.js), [`web/src/plotLayout.js`](../../web/src/plotLayout.js), [`web/src/RadialPlot.jsx`](../../web/src/RadialPlot.jsx), [`web/src/solarRv.js`](../../web/src/solarRv.js), [`web/src/SolarRvChart.jsx`](../../web/src/SolarRvChart.jsx), [`api/ti_api/main.py`](../../api/ti_api/main.py).

## 6. Known limitations
- The day ring is an SWPC estimate. The longer rings are GFZ Kp. They are not the same product. A GFZ nowcast is labeled `definitive: false` on the API row. The ring draws the number either way. The daily GFZ file also contains ap and F10.7. That whole file is kept in the raw zone with a sha256 manifest. The rings read Kp only.
- The page does not poll. Reload it to see a newer minute.
- Radius auto-scale makes a quiet day look as large as a storm. The G-scale colors and the fixed 0–9 switch are there for that. The under-plot readout and CSV have the exact numbers.
- Alerts, solar wind, and GOES stay on Grafana. This page draws Kp and the 7-day solar radial-velocity chart. Satellite altitude is on Satellite Tracking.
- The hero background is Phil Hart’s Exmouth (20 Apr 2023) total-eclipse corona photograph at 40% opacity over black (`assets/brand/CoronaExmouth_Hart_1920.jpg`, CC BY-NC-SA 4.0). A credit line links to his expedition write-up.
- Moving the pointer over a ring updates the centered readout under that plot with UTC time and Kp. There is no floating tooltip on the graphic itself.
- The layout is dark on purpose, from the design brief. `prefers-reduced-motion` turns off the live-dot blink, the view-toggle transition, and the radial↔Cartesian unwind (the view still flips instantly).
- The Change Data View control is at 10% opacity until hover or keyboard focus; on coarse pointers (`hover: none`) it stays faintly visible so a tap can find it.
- No live call against the running stack was made for this page. Tests mock the API.

## 7. Interview talking points
- **30-second pitch:** The live number is SWPC's 1-minute estimated Kp. The longer clocks are GFZ's Kp since 1932, kept in a separate table so the estimate and the definitive index are not mixed. Angle is time, radius is Kp, and the stroke fades until the next lap overwrites it.
- **Hardest problem:** The SWPC files are short, and they are a different product from GFZ. The long rings call `GET /api/v1/kp-gfz`, which allows 4200 days. The 1-minute route stays at 7 days.
- **Trade-off I made:** SVG instead of Plotly for this picture, because one Plotly line cannot fade segment by segment. Plotly is still the plan for a normal line chart.
- **How I know it works:** `web/src/kp.test.js` checks the bin average, the lap overwrite, the daily maximum, and the request windows. Playwright loads the page at 320, 375, 390, 1280, and 1440 px with a mocked API, and checks a failed API as well. Run both from `web/` with `npm test` and `npx playwright test`. The GitHub Actions workflow does not run them yet.
- **If I had more time / at scale:** Refresh the page on a timer. Add the other tiles from the design brief.
- **Likely questions & my answers:**
  - Q: "Why is twelve o'clock not 'now'?" A: "Now is the moving head. Twelve o'clock is a fixed UTC boundary, so the same hour sits in the same place every lap."
  - Q: "Why can a quiet day fill the circle?" A: "The radius auto-scales to the largest value in that window. The label and the 0–9 switch tell you which scale you are looking at."

## 8. Glossary
| Term | Plain-language meaning |
|---|---|
| Kp | A 0 to 9 index of how disturbed Earth's magnetic field is, averaged from ground magnetometers. |
| G-scale | NOAA's geomagnetic storm scale. G1 starts at Kp 5. G5 is Kp 9. |
| Lap | One trip around the ring: 24 hours, 30 days, or 365 days. |
| Estimated Kp | SWPC's real-time number. The definitive index from GFZ comes later. |
