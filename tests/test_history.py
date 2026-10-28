"""GFZ Kp backfill and Space-Track gp_history. HTTP is a fake."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx

from ti_ingest.gfz_kp import parse_gfz_text
from ti_ingest.spacetrack_gp import (
    SpaceTrackSettings,
    poll_spacetrack,
    startup_line,
)
from ti_ingest.swpc import make_client

DAY = (
    "2026 10 27 34633 34633.5 2635 2  1.667  2.333  1.667  1.333  "
    "1.667  1.000  2.000  1.000    6    9    6    5    6    4    7    4     "
    "6  16     88.8     87.7 0"
)
GAP = (
    "2026 10 26 34632 34632.5 2635 1  0.667  -1.000  1.000  1.667  "
    "1.667  1.667  0.667  0.667    3    -1    4    6    6    6    3    3     "
    "4  28     90.8     89.7 1"
)


def test_gfz_parser_expands_a_day_and_skips_a_gap() -> None:
    body = f"# comment\n{DAY}\n{GAP}\n".encode()
    rows, rejected, error = parse_gfz_text(body)
    assert error is None
    assert rejected == 0
    assert len(rows) == 15
    first = rows[0]
    assert first.time_tag == datetime(2026, 10, 27, 0, tzinfo=UTC)
    assert first.kp == 1.667
    assert first.ap == 6
    assert first.definitive is False
    assert rows[7].time_tag == datetime(2026, 10, 27, 21, tzinfo=UTC)
    hours = [row.time_tag.hour for row in rows if row.time_tag.day == 26]
    assert 3 not in hours
    assert rows[-1].definitive is True
    assert rows[-1].ap == 3


def test_gfz_parser_rejects_a_short_line_and_a_kp_past_nine() -> None:
    bad = "2026 10 01 1 1.0 1\n"
    high = DAY.replace("1.667", "9.100", 1)
    rows, rejected, error = parse_gfz_text(f"{bad}{high}\n".encode())
    assert error is None
    assert rows == []
    assert rejected == 2


def test_spacetrack_startup_hides_the_password() -> None:
    line = startup_line("/data/raw", False)
    assert "skipped" in line
    enabled = startup_line("/data/raw", True)
    assert "400" in enabled
    assert "secret" not in enabled


def test_spacetrack_logs_in_then_fetches_history(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path.endswith("/login"):
            assert request.method == "POST"
            body = request.content.decode()
            assert "identity=user" in body
            assert "password=secret" in body
            assert "secret" not in str(request.url)
            return httpx.Response(200, json={"Login": "ok"})
        assert "gp_history" in request.url.path
        assert "EPOCH" in request.url.path
        return httpx.Response(
            200,
            json=[
                {
                    "OBJECT_NAME": "ISS (ZARYA)",
                    "OBJECT_ID": "1998-067A",
                    "EPOCH": "2026-10-25T15:04:58.336608",
                    "MEAN_MOTION": 15.49052179,
                    "ECCENTRICITY": 0.00069029,
                    "INCLINATION": 51.6336,
                    "RA_OF_ASC_NODE": 150.0,
                    "ARG_OF_PERICENTER": 80.0,
                    "MEAN_ANOMALY": 280.0,
                    "NORAD_CAT_ID": 25544,
                    "BSTAR": 0.0001,
                    "MEAN_MOTION_DOT": 0.0001,
                }
            ],
        )

    settings = SpaceTrackSettings("user", "secret", True)
    with make_client(
        "TachoclineIndustries/0.1 (test)", transport=httpx.MockTransport(handler)
    ) as client:
        results = poll_spacetrack(
            client,
            tmp_path,
            settings,
            datetime(2026, 10, 27, 12, tzinfo=UTC),
        )
    assert results[0].product == "gp-hist-25544"
    assert results[0].path is not None
    assert results[0].path.suffix == ".json"
    assert seen[0].endswith("/ajaxauth/login")
    assert len(results) == 5


def test_spacetrack_stops_when_login_is_rejected(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"Login": "failed"})

    settings = SpaceTrackSettings("user", "secret", True)
    with make_client("test", transport=httpx.MockTransport(handler)) as client:
        results = poll_spacetrack(
            client,
            tmp_path,
            settings,
            datetime(2026, 10, 27, tzinfo=UTC),
        )
    assert results[0].product == "gp-hist-login"
    assert results[0].stop_run is True
    assert list(tmp_path.rglob("*.json")) == []
