# Satellite Orbit Decay and Solar Activity: Open Data Guide
_Checked 2026-10-20. ✅ = 200 OK. ⚠️ = blocks bots (403/301). The site most likely works in a browser, but this is unverified. ❌ = 404 or no response._

## 1. Orbital data sources
- **Space-Track.org** https://www.space-track.org ✅ (free account required; you must accept the user agreement). The `gp_history` class has historical TLE/GP data for every cataloged object, going back to the 1950s. The `decay` class has decay and reentry messages, and `tip` has Tracking and Impact Predictions. The API has rate limits (roughly 30 requests/min and 300/hour, per the Space-Track guidelines; confirm current limits after logging in). Download in bulk and cache the results; don't poll.
- **CelesTrak** (no account needed):
  - Current GP data: https://celestrak.org/NORAD/elements/ ✅
  - Format documentation: https://celestrak.org/NORAD/documentation/gp-data-formats.php ✅
  - SATCAT search (includes decay date): https://celestrak.org/satcat/search.php ✅
  - Supplemental GP built from operator ephemerides (Starlink, OneWeb and others), which is more accurate for Starlink: https://celestrak.org/NORAD/elements/supplemental/ ✅
  - A "decayed.php" page I guessed is ❌ 404. Use SATCAT's DECAY column instead.
- **ESA DISCOS** https://discosweb.esoc.esa.int ✅ (free account, API token). Object mass, shape and cross-section area, which you need for ballistic coefficients.
- **Aerospace Corp reentry predictions** https://aerospace.org/reentries ⚠️ 403 to curl, unverified. These are the reentry predictions that are widely cited.

## 2. Solar and geomagnetic indices
- **GFZ Potsdam Kp:** https://kp.gfz-potsdam.de/en/ ✅. It has one file with Kp, ap, Ap, sunspot number and F10.7 since 1932: https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt ✅. **This is the best single file to start with.**
- **CelesTrak space weather CSV** (Kp, Ap, F10.7 observed and adjusted, plus 81-day averages; the format the MSIS model expects): https://celestrak.org/SpaceData/SW-All.csv ✅
- **NOAA SWPC** live Kp: https://www.swpc.noaa.gov/products/planetary-k-index ✅. Explanation of storms: https://www.swpc.noaa.gov/phenomena/geomagnetic-storms ✅
- **NOAA NCEI Penticton F10.7 archive:** https://www.ngdc.noaa.gov/stp/space-weather/solar-data/solar-features/solar-radio/noontime-flux/penticton/ ✅
- **GOES X-ray flux (flares):** https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/ ✅

## 3. Thermosphere density models and Python libraries
- **NRLMSISE-00 / NRLMSIS 2.x:** https://ccmc.gsfc.nasa.gov/models/NRLMSIS~2.0/ ✅. Python wrapper **pymsis**: https://github.com/SWxTREC/pymsis ✅. It downloads the index data it needs automatically.
- **JB2008** (Jacchia-Bowman): the old jb2008.com site ❌ did not respond. The model uses extra indices (S10, M10, Y10). Python ports exist on GitHub but were not verified, so start with MSIS.
- **sgp4:** https://pypi.org/project/sgp4/ ✅
- **Skyfield:** https://rhodesmill.org/skyfield/ ✅. It loads TLEs and computes positions and altitude.

## 4. Plain explanation: how the Sun drags satellites down
The thermosphere (about 90–600 km up) is heated mainly by solar extreme-ultraviolet (EUV) light. F10.7 is the standard proxy for EUV. More EUV makes the gas hotter, the hot gas expands upward, and so a satellite at a fixed altitude flies through denser air. More density means more drag, and the orbit decays faster.

The two kinds of solar event work differently:
- **Flares:** a short burst of X-ray and EUV light. It heats the dayside within minutes, and the effect lasts hours.
- **Geomagnetic storms** (from CMEs, measured by Kp/Ap): energy pours in at the poles through electric currents (Joule heating) and particle precipitation. The heat spreads worldwide within hours. Density can rise by tens to hundreds of percent and stay high for a day or more.

The effect is largest for low, light satellites, especially right after launch.

- **February 2022 Starlink loss:** 49 satellites launched on 3 Feb 2022 into a roughly 210 km initial orbit. A minor-to-moderate storm (around G1–G2) on 3–4 Feb raised drag by up to about 50% (per SpaceX). Up to 40 of the satellites reentered. Sources: SpaceX update https://www.spacex.com/updates/ ✅ (it is an index page, so scroll to Feb 2022), and peer-reviewed analyses: "The Thermosphere Is a Drag: The 2022 Starlink Incident…" (*Space Weather*, 2022) https://doi.org/10.1029/2022SW003330 and Baruah et al. 2024 (*Space Weather*) https://doi.org/10.1029/2023SW003716 (found via search; the publisher pages return 403 to bots). **Correction (2026-10-20):** an earlier version cited arXiv 2202.13719. I checked it through the arXiv API and it is an unrelated paper ("Guarding Polygons with Holes"), so I removed it. Those two papers report 38 of 49 satellites re-entered. The SpaceNews article URL I guessed returned ❌ 404.
- **May 2024 "Gannon" storm:** a G5 (Kp 9) storm on 10–11 May 2024, the strongest since 2003. NOAA advisory: https://www.swpc.noaa.gov/news/media-advisory-noaa-forecasts-severe-solar-storm-media-availability-scheduled-friday-may-10 ✅. Recap: https://www.spaceweatherlive.com/en/news/view/545/20240514-historic-g5-geomagnetic-storm.html ✅. Widely reported effects included thousands of satellites making orbit-maintenance maneuvers at the same time, and catalog tracking being degraded for a while (Parker & Linares, 2024). **[I didn't fetch a source for the satellite effects; treat as unverified until you add a citation.]**

## 5. Proposed TI feature: "Drag Watch"
- **Satellites to track:**
  - ISS (NORAD 25544): reboosts show up as altitude jumps, so the pipeline has to detect them.
  - Hubble (20580): no propulsion, so its decay is clean and easy to read.
  - Tiangong (48274)
  - 10–20 Starlink satellites, including several from the Feb 2022 launch group (Starlink Group 4-7; look up their NORAD IDs in SATCAT by launch date).
  - One decayed cubesat
- **Pipeline:**
  1. Pull Space-Track `gp_history` for these IDs once, then fetch daily updates. Store the results in Parquet or Postgres.
  2. Compute perigee and apogee altitude from the mean motion and eccentricity: a = (μ/n²)^(1/3), perigee = a(1−e) − R⊕. Also plot the BSTAR drag term.
  3. Join with the GFZ Kp/F10.7 file by date.
  4. Plot daily altitude and daily altitude change (dh/dt) against Ap and F10.7, with storm periods shaded.
- **Starter decay model:**
  1. Regress dh/dt ≈ −k·ρ(h, F10.7, Ap), where ρ is the density from pymsis at the satellite's current altitude and k is fitted for each satellite (it absorbs the ballistic coefficient).
  2. Integrate forward under three scenarios (quiet, current, storm indices) to get a predicted reentry date.
  3. Validate against the decay dates in SATCAT.
  4. A later step is to swap in proper semi-analytic decay theory or a JB2008 port.

## 6. Storms and power grids: data
- **NERC standards:** TPL-007-4 (GMD vulnerability assessment) https://www.nerc.com/pa/Stand/Reliability%20Standards/TPL-007-4.pdf ✅. EOP-010 covers operating procedures. Standards index: https://www.nerc.com/pa/Stand/Pages/ReliabilityStandards.aspx ✅
- **FERC** GMD page https://www.ferc.gov/industries-data/electric/industry-activities/geomagnetic-disturbances ⚠️ 403 to curl, unverified.
- **Hydro-Québec, 13 Mar 1989:** the grid collapsed in about 90 seconds, leaving roughly 6 million people without power for about 9 hours. https://hydroquebec.com ✅ (homepage only; find a specific history page).
- **USGS geomagnetism:**
  - Data web service: https://geomag.usgs.gov/ws/docs/ ✅ (magnetometer time series; there may also be geoelectric-field products, but I didn't verify that).
  - Program page https://www.usgs.gov/programs/geomagnetism ⚠️ 403.
  - Geoelectric hazard page ❌ 404 (wrong URL guess).
- **NOAA NCEI geomagnetic data:** https://www.ngdc.noaa.gov/geomag/data/geomag/magnet/ ✅
- **Possible TI angle:** a time series of dB/dt (the rate of magnetic field change) from USGS observatories during 1989-style and May 2024 storms, compared with NERC benchmark thresholds.

## 7. Activity of other stars compared with the Sun
- **Mount Wilson HK Project (S-index from Ca II H&K lines, 1966–2003):** Mt Wilson Observatory https://www.mtwilson.edu ✅. The public release of the full HK Project data is **unverified**. Results are published in papers (for example Baliunas et al. 1995, ApJ 438, 269; the ADS page returned 405 to curl, so it's unverified, though it probably works in a browser).
- **California Planet Search / Keck HIRES S-index:** Isaacson & Fischer and later papers. The HIRES S-index values for thousands of stars were published in the paper's machine-readable tables (Butler et al. 2017, ApJS 230, 16: https://iopscience.iop.org/article/10.3847/1538-4365/aa56c1/meta ✅). These tables are **genuinely public**. Raw HIRES spectra are public via the Keck Observatory Archive https://koa.ipac.caltech.edu ✅.
- **NASA Exoplanet Archive** https://exoplanetarchive.ipac.caltech.edu ✅: stellar parameters, some with activity indicators.
- **Solar comparison data:** NSO https://nso.edu ✅ and the NISP/SOLIS Sun-as-a-star Ca II K record https://www.nso.edu/telescopes/nisp/ ✅ (specific download location unverified).
- **Possible TI feature:** plot the Sun's S-index cycle alongside the S-index time series of other Sun-like stars, to answer "Is our Sun unusually quiet?"
