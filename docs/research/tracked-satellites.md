# Starter set of tracked satellites

Checked 2026-10-25, evening Pacific. Catalog rows are from CelesTrak SATCAT (`https://celestrak.org/satcat/records.php`), one request per name or catalog number, `FORMAT=json`. Operational status codes are from [CelesTrak: SATCAT Operational Status](https://celestrak.org/satcat/status.php) (`+` operational, `-` nonoperational, `D` decayed). Perigee and apogee in those rows are altitudes in kilometers ([SATCAT format](https://celestrak.org/satcat/satcat-format.php)).

This is the first set to poll. It stays small. Howard's note on issue #33 starts with the International Space Station and the Landsat satellites. His comment on pull request #70 adds the Hubble Space Telescope and NASA Swift. The longer Drag Watch sample in [satellite_orbit_decay_data.md](satellite_orbit_decay_data.md) (Tiangong, a Starlink group, a decayed cubesat) stays a later idea.

Nothing here is ingested yet. Polling is issue #34. CelesTrak's rule for that poller is at most one download per group per two hours ([data_sources.md](data_sources.md)). These lookups used `NAME` or `CATNR`, not `GROUP=active`.

## The five objects

| Object | NORAD ID | International designator | Launch | SATCAT ops | Decay date | Why it is in the set |
|---|---|---|---|---|---|---|
| ISS (ZARYA) | 25544 | 1998-067A | 1998-11-20 | `+` operational | empty | The station people already know. It reboosts, so altitude jumps are real events the pipeline has to notice, not noise. |
| LANDSAT 8 | 39084 | 2013-008A | 2013-02-11 | `+` operational | empty | One of the two Landsats still carrying out the mission. A sun-synchronous Earth-observing satellite, lower than the station, so drag matters more. |
| LANDSAT 9 | 49260 | 2021-088A | 2021-09-27 | `+` operational | empty | The other operational Landsat. Same kind of orbit as Landsat 8, launched eight years later, so the pair can be compared without adding a fleet. |
| HST | 20580 | 1990-037B | 1990-04-24 | `+` operational | empty | The Hubble Space Telescope. SATCAT's name is `HST`, not `HUBBLE`. On this check perigee was 468 km and apogee 471 km. No propulsion, so its altitude change is drag rather than a reboost. |
| SWIFT | 28485 | 2004-047A | 2004-11-20 | `+` operational | empty | NASA's Neil Gehrels Swift Observatory. The catalog name is `SWIFT`. It is in the set because the orbit is decaying. See below. |

`NAME=HUBBLE` does not return HST. That search returned four other payloads whose names contain HUBBLE (catalog numbers 64562, 64565, 64592, and 64840). `NAME=HST` returns the telescope.

## Swift is still in orbit

SATCAT's `DECAY_DATE` for 28485 was empty on this check, and the ops code is `+`. Swift has not been marked decayed. The same row lists perigee 259 km and apogee 264 km.

NASA's 2026-10-23 post, [NASA's Swift Mission Ends Ahead of Re-Entry](https://science.nasa.gov/blogs/swift/2026/10/23/nasas-swift-mission-ends-ahead-of-re-entry/), says operations have ended and the spacecraft is expected to re-enter in the next few weeks. It also says drag from recent solar activity made Swift sink, and that on 2026-10-20 it reached 171 miles (275 km). So Swift is still in orbit and losing altitude. There is no reentry date to use as ground truth until SATCAT records one.

## Left out, and why

LANDSAT 7 (NORAD 25682, 1999-020A) is still in the catalog and its decay date is empty, but its ops code is `-` (nonoperational). It is not in the starter set.

The `NAME=HST` response also includes two debris pieces that have already decayed:

| Object | NORAD ID | Decay date |
|---|---|---|
| HST DEB [SOLAR PANEL] | 22920 | 1998-10-28 |
| HST DEB | 27822 | 2003-09-05 |

Those dates are real SATCAT decay dates. The pieces are not the telescope, and they are not in the starter set. Issue #33 asks for ground-truth decay dates for decayed objects in the set we track. None of the five objects above has a decay date, so that line is still open.

## What the next poller should request

Five current GP records, not a CelesTrak group file:

- `https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=json`
- `https://celestrak.org/NORAD/elements/gp.php?CATNR=39084&FORMAT=json`
- `https://celestrak.org/NORAD/elements/gp.php?CATNR=49260&FORMAT=json`
- `https://celestrak.org/NORAD/elements/gp.php?CATNR=20580&FORMAT=json`
- `https://celestrak.org/NORAD/elements/gp.php?CATNR=28485&FORMAT=json`

Those GP URLs were not fetched for this note. The SATCAT rows above are the source for the names and ids.
