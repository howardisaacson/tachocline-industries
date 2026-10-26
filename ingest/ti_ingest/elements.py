"""Two-body altitude from a TLE mean motion and eccentricity.

A TLE's mean motion is revolutions per day. Turn that into radians per
second, then the semi-major axis is the two-body result

    a = (μ / n²) ** (1/3)

with μ in km³/s² and n in radians per second. Perigee altitude is
``a * (1 - e) - R`` and apogee altitude is ``a * (1 + e) - R``. ``R`` is
Earth's equatorial radius. Both altitudes are kilometers above that
radius, not the distance from Earth's center.

μ and R are the values on NASA's Earth fact sheet: GM is
``0.39860 × 10^6`` km³/s², and the equatorial radius is 6378.137 km.
https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html

This is not an SGP4 position. A TLE mean motion is a Kozai mean motion,
and SGP4 converts it before propagating. The difference is small beside
a reboost. The format of a TLE and that conversion are documented at
https://celestrak.org/NORAD/documentation/tle-fmt.php and in Vallado,
Crawford, Hujsak, and Kelso, "Revisiting Spacetrack Report #3"
(AIAA 2006-6753),
https://celestrak.org/publications/AIAA/2006-6753/AIAA-2006-6753.pdf
"""

from __future__ import annotations

import math

# NASA Earth fact sheet. GM is quoted as 0.39860 × 10^6 km³/s².
MU_KM3_S2 = 398600.0
EQUATORIAL_RADIUS_KM = 6378.137
SECONDS_PER_DAY = 86400.0


def altitudes_km(
    mean_motion_rev_per_day: float, eccentricity: float
) -> tuple[float, float]:
    """Return ``(perigee_altitude_km, apogee_altitude_km)``.

    ``mean_motion_rev_per_day`` is the TLE mean motion. ``eccentricity``
    is dimensionless. A non-positive mean motion, or an eccentricity
    outside ``[0, 1)``, cannot describe this ellipse.
    """
    if mean_motion_rev_per_day <= 0:
        raise ValueError("mean motion must be positive")
    if eccentricity < 0 or eccentricity >= 1:
        raise ValueError("eccentricity must be in [0, 1)")
    n_rad_s = mean_motion_rev_per_day * (2.0 * math.pi) / SECONDS_PER_DAY
    semi_major_km = (MU_KM3_S2 / n_rad_s**2) ** (1.0 / 3.0)
    perigee = semi_major_km * (1.0 - eccentricity) - EQUATORIAL_RADIUS_KM
    apogee = semi_major_km * (1.0 + eccentricity) - EQUATORIAL_RADIUS_KM
    return perigee, apogee
