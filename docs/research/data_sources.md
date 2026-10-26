# Tachocline Industries: Satellite Data Sources & Starter Stack

*Researched Sun Oct 18, 2026, ~18:50–19:00 PDT. "Verified" means I fetched the URL from the box with `curl` and got HTTP 200 with fresh data at that time. Anything else is labelled.*

---

## 0. Heads-up: big 2026 changes in solar-wind data (verified)

- **DSCOVR is no longer a real-time source.** SWPC stopped ingesting DSCOVR data on **2026-06-30**. **SOLAR-1** (NOAA's SWFO-L1, launched 2025-09-24, operational 2026-06-10) is now the primary L1 solar-wind monitor. **ACE** is the backup until **NASA IMAP I-ALiRT** has 24/7 coverage. Sources: [SWPC news](https://www.spaceweather.gov/news/solar-wind-data-and-display-changes), [OSPO SOLAR-1 status](https://www.ospo.noaa.gov/operations/swfo/status.html).
- **The old `products/solar-wind/plasma-7-day.json` and `mag-*.json` endpoints are gone.** They return 404, and per [NWS SCN 26-21](https://www.weather.gov/media/notification/pdf_2026/scn26-21_Data_Format_Changes_Impacting_SWPC_Products.pdf) they were removed around 2026-04-30. Many tutorials and GitHub repos still use them. The replacements are `json/rtsw/rtsw_wind_1m.json`, `rtsw_mag_1m.json` and `rtsw_ephemerides_1h.json`. They carry `source` and `active` fields, cover only the **last ~24 h** (so you have to store history yourself), and mix several spacecraft in one file.
- In March 2026 SWPC also switched `noaa-planetary-k-index.json`, `kyoto-dst.json` and the 10.7 cm flux files from an array of arrays with a header row to proper JSON objects. Breaking upstream schema changes like this are good material for a data-engineering portfolio.

---

## 1. Data sources

| # | Source | Satellite(s) | Access | Cadence | Auth | Status |
|---|---|---|---|---|---|---|
| 1 | NOAA SWPC real-time solar wind | SOLAR-1, ACE, IMAP | Static JSON over HTTPS | 1-min records, rolling 24 h | None | ✅ verified |
| 2 | NOAA SWPC GOES X-ray flux & protons | GOES-18 (primary in feed today) | Static JSON | 1-min | None | ✅ verified |
| 3 | NOAA SWPC Kp index, alerts, aurora | Ground magnetometers + L1 wind | Static JSON | 1-min est. Kp / 3-h Kp | None | ✅ verified |
| 4 | NASA DONKI (flares, CMEs, storms) | SDO, SOHO, GOES, STEREO (event catalog) | REST JSON | Event-driven | None (CCMC) / free key (api.nasa.gov) | ⚠️ **503 at test time** |
| 5 | CelesTrak GP/TLE orbital elements | ~all tracked objects (18th SDS data) | REST (JSON/CSV/TLE/XML) | Checked every 2 h | None (strict rate policy) | ✅ verified |
| 6 | Space-Track.org | Same, authoritative source | REST JSON | Same | Free account | 🔒 401 without login (expected) |
| 7 | SatNOGS Network / DB | Hundreds of cubesats, amateur ground stations | REST JSON | Continuous observations | None (observations) / free token (telemetry) | ✅ observations verified; telemetry 401 without token |
| 8 | NASA FIRMS active fires | Suomi-NPP / NOAA-20/21 VIIRS, Terra/Aqua MODIS | CSV files; REST API | NRT < 3 h; URT ~60 s (US/Can) | None (bulk CSV) / free MAP_KEY (API) | ✅ CSV verified; API needs key |
| 9 | NOAA GOES ABI imagery | GOES-19 (East), GOES-18 (West) | JPEG CDN + public AWS S3 (NetCDF) | CONUS every 5 min | None | ✅ verified |
| 10 | NASA CMR (Earthdata search API) | Terra/Aqua/etc. (all NASA EOSDIS) | REST JSON metadata | Minutes after granule ingest | None to search; free Earthdata Login to download | ✅ verified |
| 11 | Copernicus Data Space (Sentinel) + STAC mirrors | Sentinel-1/2/3/5P | OData / STAC REST | Hours after acquisition | None to search; free account to download (per docs, not tested) | ✅ catalog verified |
| 12 | NASA SDO "latest" images | Solar Dynamics Observatory (AIA/HMI) | JPEG over HTTPS | Refreshed every few minutes (Last-Modified about 3 min old when checked) | None | ✅ verified |

Bonus (not satellite-native but related): `https://api.wheretheiss.at/v1/satellites/25544` returns ISS position as JSON (verified). `http://api.open-notify.org/iss-now.json` timed out. I skipped USGS earthquakes because they come from seismometers, not satellites.

### Details

**1. SWPC Real-Time Solar Wind**: ☀️ *the core tachocline-themed feed*
- What: solar-wind proton speed, density and temperature, plus interplanetary magnetic field (Bt, Bx/By/Bz in GSE/GSM), measured at L1, about 1.5 million km sunward. It reaches Earth roughly 15–60 min later.
- Endpoints (verified):
  - `https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json` (≈2.1 MB, 2,876 rows, sources: SOLAR1 active, ACE, IMAP)
  - `https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json`
  - `https://services.swpc.noaa.gov/json/rtsw/rtsw_ephemerides_1h.json` (listed in directory, not fetched)
- Why it shows DE skill: only a rolling 24 h window is served, so you need incremental, idempotent upserts keyed on `(time_tag, source)`. You also have to resolve which spacecraft is "active", handle gaps and nulls, and backfill history from NCEI. Bz turning south plus high speed is how storms get predicted, which makes for a good dashboard story.

**2. GOES X-ray flux / particle flux**: ☀️ solar flares in real time
- `https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json` (verified; 1-min `time_tag`, two energy bands 0.05–0.4 nm and 0.1–0.8 nm, `satellite: 18`). Also available as `-1-day`, `-3-day` and `-7-day` (not individually tested). Checked again 2026-10-25: keys are `time_tag` (with a `Z` suffix), `satellite`, `energy`, `flux`, `observed_flux`, `electron_correction`, and `electron_contaminaton` (that spelling is upstream). Issue #31 polls this 6-hour file only. The longer windows and the proton file are not polled.
- `https://services.swpc.noaa.gov/json/goes/primary/integral-protons-6-hour.json` (verified)
- Why: a log-scale time series that maps directly to flare classes (A/B/C/M/X). Good for threshold alerting and flare-event detection jobs.

**3. Kp index, alerts, aurora**: ☀️ geomagnetic response
- `https://services.swpc.noaa.gov/json/planetary_k_index_1m.json` (verified, 1-min estimated Kp)
- `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json` (verified, 3-hourly, new object format)
- `https://services.swpc.noaa.gov/products/alerts.json` (verified; today it carries a **G1 storm watch for Oct 19–20**)
- `https://services.swpc.noaa.gov/json/ovation_aurora_latest.json` (verified, global aurora probability grid of about 900 KB)
- `https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json` (verified, monthly sunspot number back to 1749, good for a long-history panel)
- Why: lets you join cause (solar wind) to effect (Kp). The aurora grid is a geospatial dataset.

**4. NASA DONKI**: ☀️ space-weather event database (flares, CMEs, geomagnetic storms, SEPs, with linked events)
- `https://api.nasa.gov/DONKI/FLR?startDate=2026-10-01&endDate=2026-10-18&api_key=DEMO_KEY` and `https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/FLR?...`
- ⚠️ **Unverified:** both hosts returned 503 or timed out on 3 attempts tonight. Retry later. A free personal key from api.nasa.gov avoids DEMO_KEY limits.
- Why: relational, nested JSON (events linked to other events) is a natural fit for normalized SQL modelling. It complements the raw time series in 1–3.

**5. CelesTrak GP data (TLE/OMM)**: orbits of everything tracked
- `https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json` (verified)
- `https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle` (verified, ISS TLE)
- ⚠️ **Rate policy ([docs](https://celestrak.org/NORAD/documentation/gp-data-formats.php)):** data refreshes every 2 h, so poll no more often. `GROUP=active` and `starlink` enforce one download per update. More than 50 HTTP 301/403/404 errors in 2 h gets your IP firewalled. Always use `.org`, not `.com`. Default format became CSV in May 2026, so pass `FORMAT=json`.
- Why: shows polite polling (conditional fetch, backoff, stopping on errors). You can propagate with SGP4 (`sgp4` / `skyfield` Python libraries) to plot live ground tracks and compute passes over Berkeley.

**6. Space-Track.org**: the authoritative source of the same GP data plus decay and conjunction data. You need a free account and must use session-cookie login. Verified that it returns 401 without login. Use CelesTrak first.

**7. SatNOGS**: a global network of open-source amateur ground stations receiving cubesat downlinks. This is the most literal "satellite data stream" on the list.
- `https://network.satnogs.org/api/observations/?format=json` (verified, no auth). Each record has station lat/lon, NORAD ID, and links to audio (`.ogg`), waterfall PNG and demodulated frames.
- `https://db.satnogs.org/api/satellites/?format=json` (verified, no auth, satellite catalog)
- `https://db.satnogs.org/api/telemetry/?satellite=<NORAD>` gives decoded telemetry frames. It **needs a free DB API token** (`Authorization: Token …`); I verified it returns 401 without one.
- Why: shows the real pipeline from raw RF to frames to decoded engineering values. It pairs with CelesTrak orbits. Paginated REST.

**8. NASA FIRMS**: active fire and thermal anomaly detections
- Bulk CSV, no key (verified, ~8.7 MB): `https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv`
- API: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/<MAP_KEY>/VIIRS_SNPP_NRT/world/1` needs a **free MAP_KEY** (limit 5,000 transactions per 10 min). The `DEMO` key returned "Invalid MAP_KEY".
- Latency: NRT < 3 h globally; ultra-real-time about 60 s over the US and Canada ([FIRMS FAQ](https://www.earthdata.nasa.gov/data/tools/firms/faq)).
- Why: geospatial points, which suit PostGIS, H3 binning and map dashboards. A California fire-season view is locally relevant. Deduplicating overlapping 24 h files is a real DE problem.

**9. NOAA GOES ABI imagery**
- Quick-look JPEG (verified, about 6–8 MB): `https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/GEOCOLOR/latest.jpg` (GOES18 for West)
- Science data on public AWS S3, no auth (verified): `https://noaa-goes19.s3.amazonaws.com/?list-type=2&prefix=ABI-L2-CMIPC/2026/291/&max-keys=3`. File names show CONUS scans every 5 min (`s2026291000117…`, `s2026291000617…`). Files are NetCDF4.
- Why: object-store ingestion (list by prefix, parse timestamps from keys), NetCDF/xarray, and big-file handling. Moving here after JSON time series shows range. NOAA also publishes SNS new-object notifications for these buckets (per NOAA Open Data docs, not tested), which would allow event-driven ingestion.

**10. NASA CMR (Common Metadata Repository)**: the search API behind Earthdata Search
- `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MOD14&page_size=2&sort_key=-start_date` (verified; newest granule is a MODIS fire NRT file from about 1.5 h earlier)
- Downloads need a free **Earthdata Login** (standard NASA policy, not tested here).
- Why: teaches discovery, search and fetch over a metadata catalog, which is how large science archives work. Python client: `earthaccess`.

**11. Copernicus / Sentinel**
- `https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-2'&$orderby=ContentDate/Start desc&$top=2` (verified; newest Sentinel-2C product acquired 2026-10-19 00:56 UTC)
- STAC: `https://catalogue.dataspace.copernicus.eu/stac/collections` (verified), plus free mirrors `https://earth-search.aws.element84.com/v1/search?collections=sentinel-2-l2a&limit=1` and `https://planetarycomputer.microsoft.com/api/stac/v1/search?collections=sentinel-2-l2a&limit=1` (both verified)
- Why: STAC is the industry-standard geospatial catalog spec. Products are large (around 700 MB), so do metadata ingestion plus on-demand clipped reads (COGs) rather than bulk downloads.

**12. NASA SDO latest imagery**: ☀️ live pictures of the Sun
- `https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0193.jpg` (verified; AIA 193 Å corona)
- Why: hero image for the site. A simple image-archiving job (hash dedup, time-lapse) is a nice side-pipeline.

**Tachocline fit:** sources 1–4 and 12 trace the full Sun-to-Earth chain. The tachocline is the shear layer at the base of the convection zone, believed to drive the solar dynamo. The dynamo produces sunspot cycles (indices file), active regions erupt (SDO, X-ray flares), CMEs and wind travel outward (DONKI, L1 solar wind), and Earth responds (Kp, aurora). That gives the site a coherent physical story, not just a pile of feeds.

---

## 2. How satellite data reaches a public API (plain language)

1. **Onboard:** instruments sample and the spacecraft packs measurements into telemetry packets (usually the CCSDS standard), often storing them on a recorder.
2. **Downlink:** data is radioed to Earth when a ground antenna is in view. LEO satellites (fire/imaging) only get a few short passes per station per day, so they dump stored data in bursts, either to polar stations or via relay satellites. GEO (GOES) and L1 spacecraft (SOLAR-1, ACE) are always visible from somewhere, so they stream continuously to a network of tracking stations. That is why space-weather data can be minute-fresh. Some satellites also broadcast "direct readout" that anyone in range can catch. FIRMS ultra-real-time (about 60 s) and SatNOGS amateur stations both work this way.
3. **Processing levels** (NASA EOSDIS definitions, [Earthdata](https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/data-processing-levels)):
   - **L0**: raw instrument data, reassembled, with comms artifacts (sync frames, headers, duplicates) removed.
   - **L1A/L1B**: time-tagged and annotated with calibration and geolocation info (L1A), then converted to physical sensor units (L1B), e.g. radiance.
   - **L2**: derived geophysical quantities at the same location and resolution, e.g. "fire here, 28 MW" or "solar wind speed 399 km/s".
   - **L3**: gridded or averaged onto uniform space-time grids (daily maps). **L4**: model output.
4. **Latency tiers:** standard science-quality products arrive about 8–40 h after observation. Near-real-time (NRT) products such as LANCE run about 1–3 h, trading some accuracy for speed. Operational space weather and GOES run in minutes.
5. **Distribution:** products land in archives (NASA DAACs, NOAA NCEI, ESA CDSE) and are exposed via catalogs (CMR, STAC), object stores (AWS S3) or simple JSON files (SWPC). Your poller sits at the very end of this chain.

---

## 3. Recommended starter stack (opinionated)

| Layer | Pick | Why / resume keyword |
|---|---|---|
| Language | **Python 3.12** + `httpx`, `pydantic` | Typed data validation at the ingestion boundary |
| Ingestion | Small poller scripts run by **APScheduler** (or cron) to start; graduate to **Prefect** or **Dagster** later | "Built scheduled ETL pipelines"; orchestration comes later and is a visible upgrade |
| Database | **PostgreSQL 16 + TimescaleDB** in Docker (add **PostGIS** for FIRMS) | Hypertables, continuous aggregates, retention policies. Skip SQLite: you would migrate in week 2 anyway. |
| Raw layer | Save every raw response to `data/raw/<source>/<date>/…json` (later S3/MinIO), then parse into tables | Bronze/silver (medallion) pattern, replayability |
| Transform | Plain SQL first; add **dbt** once you have 3+ sources | dbt is a top DE resume keyword |
| API | **FastAPI** serving clean endpoints (`/solar-wind?from=…`) | REST API design, OpenAPI docs |
| Dashboards | **Grafana** (native Postgres/Timescale) for ops-style live panels **now**; a **React + Plotly/ECharts** front end for the public portfolio site later | Grafana is fast and impressive; React shows SWE range. Use Streamlit only for quick notebooks. |
| Infra | **Docker Compose** (db + grafana + poller + api), **GitHub Actions** CI (ruff, pytest), `.env` for keys | Containerization, CI/CD, testing |
| Observability | An ingestion log table (`source, fetched_at, http_status, rows_upserted, latency`) shown as a Grafana panel | Data-quality and monitoring are what separate DE from scripting |

Repo layout suggestion: a monorepo `tachocline` with `ingest/`, `api/`, `db/migrations/`, `dashboards/` (Grafana JSON provisioning), `docker-compose.yml`.

---

## 4. First milestone: L1 solar wind end to end (about one weekend)

1. `docker compose up` starts **TimescaleDB + Grafana**.
2. Create the table `solar_wind(time_tag timestamptz, source text, active bool, proton_speed real, proton_density real, proton_temperature real, PRIMARY KEY(time_tag, source))` and make it a hypertable. Do the same for `rtsw_mag_1m` (bt, bz_gsm).
3. **Poller** (`ingest/swpc_rtsw.py`): every 5 min, GET `rtsw_wind_1m.json` and `rtsw_mag_1m.json`, archive the raw JSON, validate with pydantic, and `INSERT … ON CONFLICT DO UPDATE`. Log the run to `ingest_log`. Because the file only covers 24 h, running continuously builds your own history.
4. **Grafana dashboard:** speed, density and Bz (active source only) over 24 h and 7 d, with the GOES X-ray flux (source 2) as a second feed on a log axis. Add a stat panel for "minutes since last good ingest".
5. **Done when:** the dashboard updates live, a restart causes no duplicates or gaps, and there is a README with an architecture diagram and a screenshot. Good timing: SWPC has a **G1 watch for Oct 19–20**, so you might capture a real storm signature on day one.

Next: add Kp (to correlate with Bz), then CelesTrak + SGP4 ISS tracker, then FIRMS + PostGIS map.
