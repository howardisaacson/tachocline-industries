# Starter set of tracked satellites

Checked 2026-10-25, evening Pacific. Catalog rows are from CelesTrak SATCAT, one request per catalog number: `https://celestrak.org/satcat/records.php?CATNR=<id>&FORMAT=json`. Operational status codes are from [CelesTrak: SATCAT Operational Status](https://celestrak.org/satcat/status.php) (`+` operational, `-` nonoperational, `D` decayed).

This is the first set to poll. It is smaller on purpose. Howard's note on issue #33 says to start with the International Space Station and the Landsat satellites, and to keep the number small. The longer Drag Watch sample in [satellite_orbit_decay_data.md](satellite_orbit_decay_data.md) (Hubble, Tiangong, a Starlink group, a decayed cubesat) stays a later idea. It is not this set.

Nothing here is ingested yet. Polling is issue #34. CelesTrak's rule for that poller is at most one download per group per two hours ([data_sources.md](data_sources.md)). These three lookups used `CATNR`, not `GROUP=active`.

## The three objects

| Object | NORAD ID | International designator | Launch | SATCAT ops | Why it is in the set |
|---|---|---|---|---|---|
| ISS (ZARYA) | 25544 | 1998-067A | 1998-11-20 | `+` operational | The station people already know. It reboosts, so altitude jumps are real events the pipeline has to notice, not noise. |
| LANDSAT 8 | 39084 | 2013-008A | 2013-02-11 | `+` operational | One of the two Landsats still carrying out the mission. A sun-synchronous Earth-observing satellite, lower than the station, so drag matters more. |
| LANDSAT 9 | 49260 | 2021-088A | 2021-09-27 | `+` operational | The other operational Landsat. Same kind of orbit as Landsat 8, launched eight years later, so the pair can be compared without adding a fleet. |

`DECAY_DATE` was empty for all three on this check. None of them has a reentry date to use as ground truth.

## Left out, and why

LANDSAT 7 (NORAD 25682, 1999-020A) is still in the catalog and its decay date is also empty, but its ops code is `-` (nonoperational). It is a Landsat, and it is not in the starter set. Three objects is the small set. Adding the retired one can wait.

Older Landsats that have already reentered are not in the set either. Issue #33 also asks for ground-truth decay dates for decayed objects. This starter set has no decayed object, so that line is not filled here. A decayed example is a later addition, not a fourth satellite slipped in now.

## What the next poller should request

Three current GP records, not a CelesTrak group file:

- `https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=json`
- `https://celestrak.org/NORAD/elements/gp.php?CATNR=39084&FORMAT=json`
- `https://celestrak.org/NORAD/elements/gp.php?CATNR=49260&FORMAT=json`

Those GP URLs were not fetched for this note. The SATCAT rows above are the source for the names and ids.
