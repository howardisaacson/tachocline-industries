"""Issue #35. The Orbit decay dashboard JSON is checked without starting Grafana."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = json.loads(
    (ROOT / "dashboards" / "json" / "orbit-decay.json").read_text(encoding="utf-8")
)

_WRITE_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|GRANT|ALTER|CREATE)\b",
    re.IGNORECASE,
)

CATALOG = {
    "25544": "ISS (ZARYA)",
    "39084": "LANDSAT 8",
    "49260": "LANDSAT 9",
    "20580": "HST",
    "28485": "SWIFT",
}


def _panels_by_title() -> dict[str, dict[str, object]]:
    return {panel["title"]: panel for panel in DASHBOARD["panels"]}


def _sql_list(panel: dict[str, object]) -> list[str]:
    targets = panel["targets"]
    assert isinstance(targets, list)
    raw = [target["rawSql"] for target in targets]
    assert all(isinstance(item, str) for item in raw)
    return raw


def test_dashboard_is_full_width_and_stays_on_schema_39() -> None:
    assert DASHBOARD["uid"] == "orbit-decay"
    assert DASHBOARD["schemaVersion"] == 39
    assert DASHBOARD["time"]["from"] == "now-7d"
    titles = [panel["title"] for panel in DASHBOARD["panels"]]
    assert titles == [
        "Perigee altitude",
        "Perigee change",
        "3-hour Kp",
        "Narrow window",
    ]
    for panel in DASHBOARD["panels"]:
        grid = panel["gridPos"]
        assert grid["w"] == 24
        assert grid["x"] == 0
    description = DASHBOARD["description"]
    assert isinstance(description, str)
    assert "640" in description
    assert "320" in description
    note = _panels_by_title()["Narrow window"]["options"]
    assert isinstance(note, dict)
    assert "docs/about/orbit-decay.md" in note["content"]


def test_perigee_panel_queries_the_five_catalog_numbers() -> None:
    sql = _sql_list(_panels_by_title()["Perigee altitude"])
    assert len(sql) == 5
    joined = "\n".join(sql)
    for catnr, name in CATALOG.items():
        assert f"norad_cat_id = {catnr}" in joined
        assert f'AS "{name}"' in joined
    for statement in sql:
        assert statement.startswith("SELECT")
        assert "FROM satellite_gp" in statement
        assert "$__timeFilter(epoch)" in statement
        assert _WRITE_SQL.search(statement) is None
    panel = _panels_by_title()["Perigee altitude"]
    custom = panel["fieldConfig"]["defaults"]["custom"]
    assert custom["showPoints"] == "always"
    assert custom["axisLabel"] == "km"


def test_rate_panel_lags_outside_the_time_filter() -> None:
    """The slope has to see the previous epoch, so the filter is outside LAG."""
    sql = _sql_list(_panels_by_title()["Perigee change"])
    assert len(sql) == 5
    for statement in sql:
        assert "LAG(perigee_altitude_km) OVER (ORDER BY epoch)" in statement
        assert (
            "EXTRACT(EPOCH FROM (epoch - LAG(epoch) OVER (ORDER BY epoch)))"
            in statement
        )
        assert "/ 86400.0" in statement
        assert "km_per_day IS NOT NULL" in statement
        inner, outer = statement.split(") rates", maxsplit=1)
        assert "LAG(" in inner
        assert "$__timeFilter(epoch)" not in inner
        assert "$__timeFilter(epoch)" in outer
        assert _WRITE_SQL.search(statement) is None
    custom = _panels_by_title()["Perigee change"]["fieldConfig"]["defaults"]["custom"]
    assert custom["axisLabel"] == "km/day"
    assert custom["axisCenteredZero"] is True


def test_storm_shading_uses_three_hour_kp_at_least_5() -> None:
    annotations = DASHBOARD["annotations"]["list"]
    assert len(annotations) == 1
    storm = annotations[0]
    assert storm["enable"] is True
    assert storm["hide"] is False
    sql = storm["target"]["rawSql"]
    assert "FROM planetary_kp_3h" in sql
    assert "kp >= 5" in sql
    assert "AS time" in sql
    assert "AS timeend" in sql
    assert "INTERVAL '3 hours'" in sql
    assert "$__timeFilter(time_tag)" in sql
    assert _WRITE_SQL.search(sql) is None
    kp = _panels_by_title()["3-hour Kp"]
    kp_sql = _sql_list(kp)[0]
    assert "FROM planetary_kp_3h" in kp_sql
    assert _WRITE_SQL.search(kp_sql) is None
    steps = kp["fieldConfig"]["defaults"]["thresholds"]["steps"]
    assert steps[-1]["value"] == 5


def test_dashboard_links_to_the_about_pages() -> None:
    urls = [link["url"] for link in DASHBOARD["links"]]
    assert urls == [
        "https://github.com/howardisaacson/tachocline-industries/blob/main/docs/about/orbit-decay.md",
        "https://github.com/howardisaacson/tachocline-industries/blob/main/docs/about/satellite-gp.md",
    ]
    assert DASHBOARD["links"][0]["title"] == "About this page"
