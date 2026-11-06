# Links: where TI's data comes from

Public list of the feeds Tachocline Industries reads or plans to read. This is **not** the internal reading list in [`docs/links.md`](links.md) (articles and news). Deeper notes live in [`docs/research/data_sources.md`](research/data_sources.md). Provenance matters for the data science workflow ([ADR 0016](decisions/0016-data-science-workflow-as-first-class-feature.md)).

Each entry is a live URL plus one sentence. Credits and citation notes are at the bottom.

## Solar wind (NOAA SWPC)

- [Real-time solar wind, 1-minute plasma](https://www.swpc.noaa.gov/products/solar-wind): proton speed, density and temperature measured upstream of Earth at L1, about the last 24 hours. The link opens NOAA’s solar-wind product page, which plots plasma and the magnetic field together.
- [Real-time solar wind, 1-minute magnetic field](https://www.swpc.noaa.gov/products/solar-wind): interplanetary magnetic field strength and direction (including Bz) from the same L1 spacecraft. Same product page as the plasma link; SWPC does not publish a separate HTML page for the magnetometer.
- [SWPC Real-Time Solar Wind product page](https://www.swpc.noaa.gov/products/real-time-solar-wind): NOAA's explanation of the real-time solar wind feed and which spacecraft supply it.

## Solar flares (NOAA SWPC / GOES)

- [GOES X-ray flux, 6 hours](https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json): solar X-ray brightness from the primary GOES satellite, used to classify flares (A, B, C, M, X).
- [SWPC GOES X-ray Flux product page](https://www.swpc.noaa.gov/products/goes-x-ray-flux): what the X-ray channels mean and how flare classes are defined.

## Geomagnetic activity (Kp index)

- [SWPC estimated Kp, 1-minute](https://services.swpc.noaa.gov/json/planetary_k_index_1m.json): a near-real-time estimate of global geomagnetic activity, used for the day plot.
- [SWPC planetary K-index, 3-hourly](https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json): NOAA's 3-hour Kp values; the [product page](https://www.spaceweather.gov/products/planetary-k-index) explains the index.
- [GFZ Kp since 1932](https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt): the official Kp and ap record from GFZ Potsdam, back-filling the month, year and 11-year plots ([GFZ Kp home](https://kp.gfz.de/en/); cite as [doi:10.5880/Kp.0001](https://doi.org/10.5880/Kp.0001)).

## Space weather alerts

- [SWPC alerts, watches and warnings](https://services.swpc.noaa.gov/products/alerts.json): NOAA's official space-weather alert messages; the [product page](https://www.spaceweather.gov/products/alerts-watches-and-warnings) explains each type.

## Satellite orbits

- [CelesTrak GP data](https://celestrak.org/NORAD/documentation/gp-data-formats.php): current orbital elements for tracked satellites, used to compute perigee altitude. The format page is the human-readable description; the poller requests one catalog number at a time.
- [CelesTrak SATCAT](https://celestrak.org/satcat/satcat-format.php): catalog records for the same five satellites, including `DECAY_DATE`. The poller saves the JSON once a day. This link is the format page, not that file.
- [Space-Track](https://www.space-track.org/documentation): the US Space Force satellite catalog. A free account can supply past orbits for private checks. Those rows are not shown on this site or the public API.
- [KeepTrack](https://keeptrack.space/): a public 3D view of tracked objects. This site links to it. Tachocline does not download KeepTrack data.

## Solar radial velocity (NEID and EXPRES)

- [NExScI Solar RV Archive](https://neid.ipac.caltech.edu/search_solar.php): public Sun-as-a-star radial velocities from NEID at WIYN and EXPRES at Lowell. The poller reads the Level 2 velocity table. It does not download the spectra. The [help page](https://neid.ipac.caltech.edu/help_solar.php) describes the columns.

## Solar images

- [NASA SDAC Solar Images](https://umbra.nascom.nasa.gov/newsite/images.html): NASA Goddard's Solar Data Analysis Center gallery of current solar images from several observatories (added by Howard 2026-10-30; not yet ingested).
- [SDO AIA / LMSAL](https://aia.lmsal.com/index.htm): Atmospheric Imaging Assembly images and context from Lockheed Martin Solar and Astrophysics Laboratory ([LMSAL home](https://www.lmsal.com/)); not yet ingested.

## Credits and terms

- **NOAA SWPC:** public real-time space-weather products. Credit NOAA Space Weather Prediction Center on pages that show the data. Feeds are provisional / real-time unless marked otherwise.
- **GFZ German Research Centre for Geosciences:** Kp, ap, Ap, SN, and F10.7 series. Cite Matzka, J., Stolle, C., Yamazaki, Y., Bronkalla, O. and Morschhauser, A., 2021. The geomagnetic Kp index and derived indices of geomagnetic activity. *Space Weather*, doi:[10.5880/Kp.0001](https://doi.org/10.5880/Kp.0001). See also [kp.gfz.de](https://kp.gfz.de/en/).
- **CelesTrak:** GP elements used for the public perigee chart. Credit CelesTrak (Dr. T.S. Kelso). The [usage policy](https://celestrak.org/usage-policy.php) (updated 2026 May 22) is an access rule: download only what you need, once per update (GP data every 2 hours), and stop on any HTTP status other than 200. It is not a license to republish Space-Track data.
- **Space-Track (18th Space Defense Squadron):** the [user agreement](https://www.space-track.org/documentation) forbids transferring the data or analysis of it without approval. Tachocline does not put Space-Track rows, or altitudes and rates derived from them, on the public site or the public API. Local Grafana may still read them.
- **NASA SDAC / SDO AIA / LMSAL:** public solar imagery galleries; credit the observatory named on each image page when imagery is shown on TI.
- **NEID and EXPRES, via NExScI:** public solar Level 2 velocities. Credit NEID (WIYN, NN-EXPLORE), EXPRES (Lowell Discovery Telescope), and the NASA Exoplanet Science Institute. The acknowledgement text is on the [solar help page](https://neid.ipac.caltech.edu/help_solar.php). Checked 2026-11-05. The spectra stay on the archive.
