"""Issue #28 checks for the provisioned Grafana dashboard.

They parse the JSON and read the YAML as text. They do not start Grafana
or Postgres. A dashboard is a saved layout of charts. Provisioning means
Grafana creates that layout from files in git when the container starts,
instead of someone clicking it together in the UI.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARDS = ROOT / "dashboards"
DATASOURCE = (DASHBOARDS / "provisioning" / "datasources" / "timescale.yaml").read_text(
    encoding="utf-8"
)
PROVIDER = (DASHBOARDS / "provisioning" / "dashboards" / "solar-wind.yaml").read_text(
    encoding="utf-8"
)
DASHBOARD = json.loads(
    (DASHBOARDS / "json" / "solar-wind.json").read_text(encoding="utf-8")
)

# Whole words only, so a column comment cannot trip the check.
_WRITE_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|GRANT|ALTER|CREATE)\b",
    re.IGNORECASE,
)


def _panels_by_title() -> dict[str, dict[str, object]]:
    return {panel["title"]: panel for panel in DASHBOARD["panels"]}


def _sql(panel: dict[str, object]) -> str:
    targets = panel["targets"]
    assert isinstance(targets, list)
    raw = targets[0]["rawSql"]
    assert isinstance(raw, str)
    return raw


def test_datasource_uses_the_readonly_role_and_no_password_literal() -> None:
    assert "user: $__env{TI_READONLY_USER}" in DATASOURCE
    assert "password: $__env{TI_READONLY_PASSWORD}" in DATASOURCE
    assert "database: $__env{POSTGRES_DB}" in DATASOURCE
    assert "uid: tachocline-pg" in DATASOURCE
    assert "timescaledb: true" in DATASOURCE
    assert "sslmode: disable" in DATASOURCE
    assert "editable: false" in DATASOURCE
    assert "change-me" not in DATASOURCE
    assert "ti_admin" not in DATASOURCE
    assert "POSTGRES_PASSWORD" not in DATASOURCE
    assert "updateIntervalSeconds: 30" in PROVIDER
    assert "allowUiUpdates: false" in PROVIDER
    assert "path: /etc/grafana/dashboards" in PROVIDER


def test_panels_are_full_width_rows() -> None:
    """A 24-column row is the whole grid, so a narrow window stacks them."""
    titles = [panel["title"] for panel in DASHBOARD["panels"]]
    assert titles == [
        "Proton speed",
        "Proton density",
        "Bz (GSM)",
        "Minutes since last good ingest",
        "Narrow window",
    ]
    for panel in DASHBOARD["panels"]:
        grid = panel["gridPos"]
        assert grid["w"] == 24
        assert grid["x"] == 0
    description = DASHBOARD["description"]
    assert "640" in description
    assert "320" in description
    note = _panels_by_title()["Narrow window"]["options"]
    assert isinstance(note, dict)
    assert "640" in note["content"]
    assert "320" in note["content"]


def test_measurement_queries_are_select_time_buckets_for_the_active_source() -> None:
    panels = _panels_by_title()
    expected = {
        "Proton speed": ("solar_wind", "proton_speed"),
        "Proton density": ("solar_wind", "proton_density"),
        "Bz (GSM)": ("rtsw_mag_1m", "bz_gsm"),
    }
    for title, (table, column) in expected.items():
        sql = _sql(panels[title])
        assert sql.startswith("SELECT")
        assert "time_bucket('1 minute', time_tag)" in sql
        assert f"avg({column})" in sql
        assert f"FROM {table}" in sql
        assert "AND active" in sql
        assert "$__timeFilter(time_tag)" in sql
        assert _WRITE_SQL.search(sql) is None
        assert "ingest_log" not in sql


def test_pipeline_health_reads_ingest_log_only() -> None:
    sql = _sql(_panels_by_title()["Minutes since last good ingest"])
    assert sql.startswith("SELECT")
    assert "FROM ingest_log" in sql
    assert "error IS NULL" in sql
    assert "solar_wind" not in sql
    assert "rtsw_mag_1m" not in sql
    assert "time_bucket" not in sql
    assert _WRITE_SQL.search(sql) is None
    panel = _panels_by_title()["Minutes since last good ingest"]
    assert panel["fieldConfig"]["defaults"]["noValue"] == "no good ingest"


def test_dashboard_links_to_the_solar_wind_about_page() -> None:
    """ADR 0009: the Grafana dashboard links to docs/about/solar-wind.md."""
    links = DASHBOARD["links"]
    assert isinstance(links, list)
    urls = [link["url"] for link in links]
    assert urls == [
        "https://github.com/howardisaacson/tachocline-industries/blob/main/docs/about/solar-wind.md"
    ]
    assert links[0]["title"] == "About this page"
    note = _panels_by_title()["Narrow window"]["options"]
    assert isinstance(note, dict)
    assert "docs/about/solar-wind.md" in note["content"]
