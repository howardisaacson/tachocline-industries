"""Time-ordered decay backtest. The fixture numbers are CelesTrak plus GFZ."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from analysis.backtest.decay import (
    FIXTURES,
    DecayObject,
    Element,
    activity_level,
    altitude_band,
    coverage,
    days_from_slope,
    load_starlink_2022,
    score_object,
    score_starlink_2022,
    summarize,
)

ROOT = Path(__file__).resolve().parents[1]


def _element(hour: int, perigee: float, *, day: int = 1, ndot: float = 0.1) -> Element:
    return Element(
        norad_cat_id=1,
        epoch=datetime(2022, 2, day, hour, tzinfo=UTC),
        perigee_km=perigee,
        mean_motion=15.5,
        eccentricity=0.001,
        mean_motion_dot=ndot,
    )


def test_slope_reaches_120_km_in_three_days() -> None:
    older = _element(0, 200.0)
    newer = _element(0, 180.0, day=2)
    # 20 km down in one day, 60 km left to 120 km.
    assert days_from_slope(older, newer, 120.0) == 3.0


def test_future_epoch_does_not_change_the_forecast() -> None:
    decay = datetime(2022, 2, 10, tzinfo=UTC)
    before = _element(0, 200.0, day=8)
    leaked = Element(
        norad_cat_id=1,
        epoch=datetime(2022, 2, 12, tzinfo=UTC),
        perigee_km=50.0,
        mean_motion=16.5,
        eccentricity=0.001,
        mean_motion_dot=2.0,
    )
    obj = DecayObject(1, "TEST", decay, (before, leaked))
    kp = {date(2022, 2, 9): 2.0}
    scored = score_object(obj, kp_by_day=kp, horizons=(1,))
    without = score_object(
        DecayObject(1, "TEST", decay, (before,)),
        kp_by_day=kp,
        horizons=(1,),
    )
    assert scored[0].error_days == without[0].error_days
    assert scored[0].reason == "scored"


def test_horizon_30_ignores_an_element_from_the_last_week() -> None:
    decay = datetime(2022, 2, 20, tzinfo=UTC)
    late = _element(0, 180.0, day=18)
    obj = DecayObject(1, "TEST", decay, (late,))
    scores = {item.horizon_days: item for item in score_object(obj, kp_by_day={})}
    assert scores[30].reason == "no element near cutoff"
    assert scores[1].reason == "scored"


def test_activity_and_altitude_bands() -> None:
    assert activity_level(3.9) == "quiet"
    assert activity_level(4.0) == "active"
    assert activity_level(5.0) == "storm"
    assert altitude_band(199) == "under 200 km"
    assert altitude_band(200) == "200-350 km"
    assert altitude_band(350) == "over 350 km"


def test_starlink_group_is_time_ordered_and_matches_the_page() -> None:
    scores = score_starlink_2022()
    objects, _kp = load_starlink_2022()
    assert len(objects) == 12
    by_horizon = coverage(scores)
    assert by_horizon[0]["horizon_days"] == 30
    assert by_horizon[0]["scored"] == 0
    scored = [item for item in scores if item.reason == "scored"]
    assert scored
    assert all(item.horizon_days in (7, 1) for item in scored)
    rows = summarize(scores)
    assert rows
    page = (ROOT / "docs/data-science-workflow.md").read_text(encoding="utf-8")
    for row in by_horizon:
        assert f"| {row['horizon_days']} | {row['objects']} | {row['scored']} |" in page
    for row in rows:
        mae = row["median_abs_days"]
        assert isinstance(mae, float)
        assert (
            f"| {row['horizon_days']} | {row['altitude_band']} | {row['activity']} | {row['n']} | {mae:.1f} |"
            in page
        )


def test_fixture_hashes_match_the_manifest() -> None:
    sources = json.loads((FIXTURES / "sources.json").read_text(encoding="utf-8"))
    import hashlib

    for item in sources["files"]:
        body = (FIXTURES / item["file"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == item["sha256"]
        assert "secret" not in item["url"]
