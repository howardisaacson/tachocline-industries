"""NEID and EXPRES Level 2 scalars. Network is mocked. The sample numbers are real rows read on 2026-11-05."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from ti_ingest.solar_rv import (
    TAP_SYNC_URL,
    fetch_solar_rv,
    julian_day,
    parse_solar_csv,
)

WHEN = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

NEID_CSV = b"""\
obsdate,ccfrvmod,dvrms,extsnr,exptime,ccfjdsum
"2026-11-02 17:17:50.000001",-0.6401,0.0003,407.2,55,2461346.2
"2026-11-02 17:20:00",,0.0003,400,55,2461346.2
"2026-11-02 17:22:00",20,9999,0.1,55,2461346.2
"""

EXPRES_CSV = b"""\
obsdate,ccfrvmod,dvrms,v,e_v,extsnr,exptime,ccfjdsum
"2024-09-30 15:35:58.000001",-0.6406,19.692,-64057.073,19.692,369,180,2460584.1
"""


def test_julian_day_of_a_utc_midnight() -> None:
    moment = datetime(2026, 10, 22, tzinfo=UTC)
    assert julian_day(moment) == 2461335.5


def test_neid_km_s_becomes_m_s_and_a_blank_rv_is_a_gap() -> None:
    rows, rejected, error = parse_solar_csv(NEID_CSV, "solar-rv-neid")
    assert error is None
    assert rejected == 0
    assert len(rows) == 3
    assert rows[0].rv_m_s == pytest.approx(-640.1)
    assert rows[0].rv_error_m_s == pytest.approx(0.3)
    assert rows[0].archive_time_scale == "BJD"
    assert rows[0].instrument == "neid"
    assert rows[1].rv_m_s is None
    assert rows[1].time_tag == datetime(2026, 11, 2, 17, 20, tzinfo=UTC)
    # 20 km/s with dvrms 9999 is a failed exposure, stored as a gap.
    assert rows[2].rv_m_s is None
    assert rows[2].rv_error_m_s is None


def test_expres_error_uses_e_v_in_cm_s_not_dvrms_as_km_s() -> None:
    """19.692 labeled km/s would be 19692 m/s. e_v in cm/s is 0.19692 m/s."""
    rows, rejected, error = parse_solar_csv(EXPRES_CSV, "solar-rv-expres")
    assert error is None
    assert rejected == 0
    assert len(rows) == 1
    assert rows[0].rv_m_s == pytest.approx(-640.6)
    assert rows[0].rv_error_m_s == pytest.approx(0.19692)
    assert rows[0].archive_time_scale == "JD"
    assert rows[0].instrument == "expres"


def test_tap_error_body_is_not_a_table() -> None:
    rows, rejected, error = parse_solar_csv(
        b"Failed to execute select", "solar-rv-neid"
    )
    assert rows == []
    assert rejected == 0
    assert error == "TAP returned an error instead of CSV"


def test_fetch_posts_both_tables_and_stops_on_429(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.content.decode())
        if "neidsolarl2" in seen[-1]:
            return httpx.Response(200, content=NEID_CSV)
        return httpx.Response(429, text="slow down")

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        headers={"User-Agent": "TachoclineIndustries/test"},
    )
    results = fetch_solar_rv(client, tmp_path, WHEN)
    assert [item.product for item in results] == ["solar-rv-neid", "solar-rv-expres"]
    assert results[0].path is not None
    assert results[0].path.suffix == ".csv"
    assert results[1].path is None
    assert results[1].stop_run is True
    assert all("obsjd" in query for query in seen)
    assert TAP_SYNC_URL.startswith("https://neid.ipac.caltech.edu/TAP/sync")
