"""Score a decay forecast using only data from before the decision time.

The truth is a SATCAT calendar date. The forecast at horizon H may use
element sets whose epoch is at or before ``decay date minus H days``, and
only if that epoch is within 36 hours of the cutoff. A first element from
months earlier is not the orbit "at" that cutoff, so it is not scored.

Persistence, when two eligible epochs exist, continues the recent perigee
slope until 120 km. With one eligible epoch it continues the published
mean-motion rate (``MEAN_MOTION_DOT``) and holds eccentricity fixed. Both
are baselines. The physics-lite density model is a later issue.

Altitude uses the same two-body formula as the poller
(``ti_ingest.elements.altitudes_km``).
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from ti_ingest.elements import (
    EQUATORIAL_RADIUS_KM,
    MU_KM3_S2,
    SECONDS_PER_DAY,
    altitudes_km,
)

HORIZONS_DAYS = (30, 7, 1)
REENTRY_KM = 120.0
MAX_EPOCH_AGE = timedelta(hours=36)
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@dataclass(frozen=True)
class Element:
    """One public element set reduced to the fields the baseline uses."""

    norad_cat_id: int
    epoch: datetime
    perigee_km: float
    mean_motion: float
    eccentricity: float
    mean_motion_dot: float


@dataclass(frozen=True)
class DecayObject:
    """One catalog object that has a SATCAT decay date."""

    norad_cat_id: int
    name: str
    decay: datetime
    elements: tuple[Element, ...]


@dataclass(frozen=True)
class Score:
    """One object at one horizon. ``error_days`` is None when it was not scored."""

    norad_cat_id: int
    horizon_days: int
    altitude_band: str | None
    activity: str | None
    error_days: float | None
    reason: str


def activity_level(kp: float) -> str:
    """Quiet, active, or storm from a Kp value. G1 starts at 5."""
    if kp < 4:
        return "quiet"
    if kp < 5:
        return "active"
    return "storm"


def altitude_band(perigee_km: float) -> str:
    """Three bands. The Feb 2022 objects sit in the lower two."""
    if perigee_km < 200:
        return "under 200 km"
    if perigee_km < 350:
        return "200-350 km"
    return "over 350 km"


def days_from_slope(older: Element, newer: Element, reentry_km: float) -> float | None:
    """Days from ``newer`` until perigee hits ``reentry_km`` if the slope holds.

    A slope that is flat or upward does not predict decay. A perigee that is
    already at the threshold is a decay now, which is zero days.
    """
    elapsed_days = (newer.epoch - older.epoch).total_seconds() / 86400.0
    if elapsed_days <= 0:
        return None
    slope = (newer.perigee_km - older.perigee_km) / elapsed_days
    if newer.perigee_km <= reentry_km:
        return 0.0
    if slope >= 0:
        return None
    return (reentry_km - newer.perigee_km) / slope


def days_from_ndot(element: Element, reentry_km: float) -> float | None:
    """Days until perigee hits ``reentry_km`` if mean motion keeps its rate.

    Eccentricity is held fixed. A non-positive ``MEAN_MOTION_DOT`` is not
    a decaying orbit under this baseline.
    """
    if element.perigee_km <= reentry_km:
        return 0.0
    if element.mean_motion_dot <= 0:
        return None
    a_target = (reentry_km + EQUATORIAL_RADIUS_KM) / (1.0 - element.eccentricity)
    n_rad = math.sqrt(MU_KM3_S2 / a_target**3)
    n_rev = n_rad * SECONDS_PER_DAY / (2.0 * math.pi)
    if n_rev <= element.mean_motion:
        return 0.0
    return (n_rev - element.mean_motion) / element.mean_motion_dot


def _eligible(elements: tuple[Element, ...], cutoff: datetime) -> list[Element]:
    chosen = [
        item
        for item in elements
        if item.epoch <= cutoff and cutoff - item.epoch <= MAX_EPOCH_AGE
    ]
    chosen.sort(key=lambda item: item.epoch)
    return chosen


def score_object(
    obj: DecayObject,
    *,
    kp_by_day: dict[date, float],
    horizons: tuple[int, ...] = HORIZONS_DAYS,
) -> list[Score]:
    """Score one object. Epochs after the cutoff are ignored."""
    scores: list[Score] = []
    for horizon in horizons:
        cutoff = obj.decay - timedelta(days=horizon)
        eligible = _eligible(obj.elements, cutoff)
        if not eligible:
            scores.append(
                Score(
                    obj.norad_cat_id,
                    horizon,
                    None,
                    None,
                    None,
                    "no element near cutoff",
                )
            )
            continue
        latest = eligible[-1]
        if len(eligible) >= 2:
            days = days_from_slope(eligible[-2], latest, REENTRY_KM)
        else:
            days = days_from_ndot(latest, REENTRY_KM)
        if days is None:
            scores.append(
                Score(
                    obj.norad_cat_id,
                    horizon,
                    altitude_band(latest.perigee_km),
                    _activity(kp_by_day, cutoff.date()),
                    None,
                    "persistence does not decay",
                )
            )
            continue
        predicted = latest.epoch + timedelta(days=days)
        error_days = (predicted - obj.decay).total_seconds() / 86400.0
        scores.append(
            Score(
                obj.norad_cat_id,
                horizon,
                altitude_band(latest.perigee_km),
                _activity(kp_by_day, cutoff.date()),
                error_days,
                "scored",
            )
        )
    return scores


def _activity(kp_by_day: dict[date, float], day: date) -> str:
    kp = kp_by_day.get(day)
    if kp is None:
        return "Kp missing"
    return activity_level(kp)


def median_absolute_error(errors: list[float]) -> float | None:
    if not errors:
        return None
    return statistics.median(abs(error) for error in errors)


def summarize(scores: list[Score]) -> list[dict[str, object]]:
    """One row per horizon, altitude band, and activity, for scored forecasts only."""
    groups: dict[tuple[int, str, str], list[float]] = {}
    for score in scores:
        if (
            score.error_days is None
            or score.altitude_band is None
            or score.activity is None
        ):
            continue
        key = (score.horizon_days, score.altitude_band, score.activity)
        groups.setdefault(key, []).append(score.error_days)
    rows: list[dict[str, object]] = []
    for key in sorted(groups):
        errors = groups[key]
        rows.append(
            {
                "horizon_days": key[0],
                "altitude_band": key[1],
                "activity": key[2],
                "n": len(errors),
                "median_abs_days": median_absolute_error(errors),
            }
        )
    return rows


def coverage(scores: list[Score]) -> list[dict[str, object]]:
    """How many decayed objects could be scored at each horizon."""
    rows = []
    for horizon in HORIZONS_DAYS:
        subset = [score for score in scores if score.horizon_days == horizon]
        rows.append(
            {
                "horizon_days": horizon,
                "objects": len(subset),
                "scored": sum(1 for score in subset if score.reason == "scored"),
                "no_element": sum(
                    1 for score in subset if score.reason == "no element near cutoff"
                ),
                "not_decaying": sum(
                    1
                    for score in subset
                    if score.reason == "persistence does not decay"
                ),
            }
        )
    return rows


def load_starlink_2022(
    fixtures: Path = FIXTURES,
) -> tuple[list[DecayObject], dict[date, float]]:
    """Load the committed CelesTrak extracts and the GFZ daily-max excerpt."""
    sources = json.loads((fixtures / "sources.json").read_text(encoding="utf-8"))
    catalog = json.loads(
        (fixtures / "satcat_2022-010.json").read_text(encoding="utf-8")
    )
    elements: dict[int, list[Element]] = {}
    for name in ("gp_first_2022-010.json", "gp_last_2022-010.json"):
        for row in json.loads((fixtures / name).read_text(encoding="utf-8")):
            perigee, _apogee = altitudes_km(
                float(row["MEAN_MOTION"]), float(row["ECCENTRICITY"])
            )
            epoch = datetime.fromisoformat(row["EPOCH"]).replace(tzinfo=UTC)
            elements.setdefault(int(row["NORAD_CAT_ID"]), []).append(
                Element(
                    norad_cat_id=int(row["NORAD_CAT_ID"]),
                    epoch=epoch,
                    perigee_km=perigee,
                    mean_motion=float(row["MEAN_MOTION"]),
                    eccentricity=float(row["ECCENTRICITY"]),
                    mean_motion_dot=float(row["MEAN_MOTION_DOT"]),
                )
            )
    objects: list[DecayObject] = []
    for row in catalog:
        decay_text = str(row.get("DECAY_DATE") or "").strip()
        if not decay_text:
            continue
        decay = datetime.fromisoformat(decay_text).replace(tzinfo=UTC)
        cid = int(row["NORAD_CAT_ID"])
        objects.append(
            DecayObject(
                norad_cat_id=cid,
                name=str(row["OBJECT_NAME"]),
                decay=decay,
                elements=tuple(
                    sorted(elements.get(cid, []), key=lambda item: item.epoch)
                ),
            )
        )
    kp = {
        date.fromisoformat(day): float(value)
        for day, value in sources["kp"]["daily_max_kp"].items()
    }
    return objects, kp


def score_starlink_2022(fixtures: Path = FIXTURES) -> list[Score]:
    """Score every 2022-010 object that has a SATCAT decay date."""
    objects, kp = load_starlink_2022(fixtures)
    scores: list[Score] = []
    for obj in objects:
        scores.extend(score_object(obj, kp_by_day=kp))
    return scores
