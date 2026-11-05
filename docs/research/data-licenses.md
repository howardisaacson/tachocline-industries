# Data licenses

Checked 2026-11-01. Recheck on or before 2027-11-01, and sooner if a source changes its page. A new source does not go on the public site until it has a section here ([ADR 0035](../decisions/0035-what-may-be-shown-publicly.md)).

## CelesTrak

Source: [CelesTrak usage policy](https://celestrak.org/usage-policy.php), by Dr. T.S. Kelso, 2026 May 15, updated 2026 May 22. Checked 2026-11-01.

The policy is about how often a program may download, not a copyright license. The lines that bind this repo:

> Only download the data you need, when you are going to use it, and only download data once per update.
>
> For GP data, updates are once every 2 hours.
>
> Most importantly, we send HTTP error responses when users are exceeding limits or using incorrect (long-outdated) URLs (e.g., HTTP 301, 403, 404, 50x). M2M (machine-to-machine) software should immediately stop querying when it receives any non-HTTP 200 responses and report the results to a human for investigation.

Plain language: fetch one catalog number when the two-hour job runs, not a whole group file, and stop the run on a 4xx. The public perigee chart may show altitudes computed from those files if the page credits CelesTrak. The policy does not say Tachocline may redistribute data that came from Space-Track.

A 2005 Air Force Space Command letter, quoted on [CelesTrak's system notices](https://celestrak.org/NORAD/elements/notice.php) as Update #14 (2005 March 25), approved CelesTrak itself to redistribute TLEs for one year and asked for annual revalidation. That letter is not an approval for this site. This check did not find a current written grant for Tachocline Industries.

## NOAA SWPC

The real-time JSON products are US government works. Credit NOAA Space Weather Prediction Center on every page that plots them. The values are provisional until a product says otherwise. Pages already do this on the home page and the Links page.

## GFZ

The file `Kp_ap_Ap_SN_F107_since_1932.txt` says, in its header:

> LICENSE: CC BY 4.0, except for the sunspot numbers contained in this file, which have the CC BY-NC 4.0 license

Cite Matzka et al., doi:[10.5880/Kp.0001](https://doi.org/10.5880/Kp.0001). This repo stores Kp and ap and does not store the sunspot number ([ADR 0022](../decisions/0022-store-gfz-kp-apart-from-swpc-estimates.md)).

## NExScI Solar RV Archive (NEID and EXPRES)

Source: [Solar RV Archive help](https://neid.ipac.caltech.edu/help_solar.php), checked 2026-11-05.

The page says NEID and EXPRES solar data are public and visible to all users. It does not state a copyright license. It does ask for this acknowledgement when NEID data appear in a publication:

> This paper contains data taken with the NEID instrument, which was funded by the NASA-NSF Exoplanet Observational Research (NN-EXPLORE) partnership and built by Pennsylvania State University. NEID is installed on the WIYN telescope, which is operated by the National Optical Astronomy Observatory, and the NEID archive is operated by the NASA Exoplanet Science Institute at the California Institute of Technology. NN-EXPLORE is managed by the Jet Propulsion Laboratory, California Institute of Technology under contract with the National Aeronautics and Space Administration.

Plain language: the public site may plot the solar velocities if the page credits NEID, EXPRES, and the NExScI archive and links to that help page. Tachocline stores the Level 2 scalar columns only. It does not redistribute the FITS files. EXPRES is released on the same archive. This check did not find a separate EXPRES copyright grant. Recheck with the NEID section on or before 2027-11-01.

## Space-Track

The user agreement, summarized from the text on the [Space-Track documentation](https://www.space-track.org/documentation) page and quoted in issue #105, forbids transferring data received from that site, or the analysis of it, without prior express approval. Public pages and the public API count as a transfer. Local Grafana and private notebooks do not. No approval email has been sent. If one is granted, record it here and revisit [ADR 0035](../decisions/0035-what-may-be-shown-publicly.md).
