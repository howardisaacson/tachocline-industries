"""Read-only API (issue #36). The database is a fake. TestClient calls the app in-process."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Self

import psycopg
import pytest
from fastapi.testclient import TestClient

from ti_api.main import app, get_connection, utc_now
from ti_api.queries import (
    ALERTS_SQL,
    GOES_SQL,
    HEALTH_SQL,
    INGEST_LOG_SQL,
    KP_1M_SQL,
    KP_3H_SQL,
    MAG_SQL,
    PERIGEE_SQL,
    SOLAR_WIND_SQL,
    SOURCES_SQL,
)

NOW = datetime(2026, 10, 26, 5, 0, tzinfo=UTC)
MINUTE = datetime(2026, 10, 26, 4, 0, tzinfo=UTC)

_WRITE_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|GRANT|ALTER|CREATE)\b",
    re.IGNORECASE,
)


class FakeCursor:
    def __init__(self, conn: FakeConn) -> None:
        self.conn = conn

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] = ()) -> None:
        if self.conn.fail:
            raise psycopg.OperationalError("db down")
        self.conn.calls.append((query, params))

    def fetchall(self) -> list[dict[str, object]]:
        return self.conn.rows


class FakeConn:
    def __init__(
        self, rows: list[dict[str, object]] | None = None, *, fail: bool = False
    ) -> None:
        self.rows = rows or []
        self.fail = fail
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def client():
    conn = FakeConn()

    def override_conn() -> Iterator[FakeConn]:
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_connection] = override_conn
    app.dependency_overrides[utc_now] = lambda: NOW
    test_client = TestClient(app)
    test_client.conn = conn  # type: ignore[attr-defined]
    yield test_client
    app.dependency_overrides.clear()


def test_queries_are_selects_with_placeholders() -> None:
    for sql in (
        HEALTH_SQL,
        SOLAR_WIND_SQL,
        SOURCES_SQL,
        INGEST_LOG_SQL,
        MAG_SQL,
        GOES_SQL,
        KP_1M_SQL,
        KP_3H_SQL,
        ALERTS_SQL,
        PERIGEE_SQL,
    ):
        assert sql.startswith("SELECT")
        assert _WRITE_SQL.search(sql) is None
    assert sql_placeholders(SOLAR_WIND_SQL) == 3
    assert "%s" in SOURCES_SQL
    assert "%s" in INGEST_LOG_SQL


def sql_placeholders(sql: str) -> int:
    return sql.count("%s")


def test_health_selects_one(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert client.conn.calls[0][0] == HEALTH_SQL  # type: ignore[attr-defined]
    assert client.conn.closed is True  # type: ignore[attr-defined]


def test_health_is_503_when_the_query_fails(client: TestClient) -> None:
    client.conn.fail = True  # type: ignore[attr-defined]
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["detail"] == "database unavailable"


def test_solar_wind_defaults_to_six_hours_and_returns_rows(client: TestClient) -> None:
    client.conn.rows = [  # type: ignore[attr-defined]
        {
            "time_tag": MINUTE,
            "source": "ACE",
            "active": True,
            "proton_speed": 420.0,
            "proton_density": 4.5,
            "proton_temperature": 80000.0,
        }
    ]
    response = client.get("/api/solar-wind")
    assert response.status_code == 200
    body = response.json()
    assert body["processing_level"] == "real-time"
    assert body["limit"] == 500
    assert body["time_to"] == "2026-10-26T05:00:00Z"
    assert body["time_from"] == "2026-10-25T23:00:00Z"
    assert body["rows"][0]["source"] == "ACE"
    assert body["rows"][0]["proton_speed"] == 420.0
    sql, params = client.conn.calls[0]  # type: ignore[attr-defined]
    assert sql == SOLAR_WIND_SQL
    assert params[2] == 500
    assert params[1] - params[0] == timedelta(hours=6)


def test_solar_wind_rejects_a_range_over_seven_days(client: TestClient) -> None:
    response = client.get(
        "/api/solar-wind",
        params={"from": "2026-10-01T00:00:00Z", "to": "2026-10-18T00:00:00Z"},
    )
    assert response.status_code == 422
    assert client.conn.calls == []  # type: ignore[attr-defined]


def test_solar_wind_rejects_a_naive_timestamp_and_a_backwards_window(
    client: TestClient,
) -> None:
    naive = client.get("/api/solar-wind", params={"from": "2026-10-26T00:00:00"})
    assert naive.status_code == 422
    backwards = client.get(
        "/api/solar-wind",
        params={"from": "2026-10-26T05:00:00Z", "to": "2026-10-26T04:00:00Z"},
    )
    assert backwards.status_code == 422
    assert client.conn.calls == []  # type: ignore[attr-defined]


def test_solar_wind_limit_stops_at_2000(client: TestClient) -> None:
    response = client.get("/api/solar-wind", params={"limit": 2001})
    assert response.status_code == 422
    kept = client.get(
        "/api/solar-wind",
        params={
            "from": "2026-10-26T00:00:00Z",
            "to": "2026-10-26T05:00:00Z",
            "limit": 10,
        },
    )
    assert kept.status_code == 200
    assert client.conn.calls[0][1][2] == 10  # type: ignore[attr-defined]


def test_sources_and_ingest_log_pass_the_limit(client: TestClient) -> None:
    client.conn.rows = [  # type: ignore[attr-defined]
        {"source": "ACE", "rows": 3, "latest": MINUTE}
    ]
    sources = client.get("/api/sources", params={"limit": 20})
    assert sources.status_code == 200
    assert sources.json() == [
        {"source": "ACE", "rows": 3, "latest": "2026-10-26T04:00:00Z"}
    ]
    assert client.conn.calls[0][0] == SOURCES_SQL  # type: ignore[attr-defined]
    assert client.conn.calls[0][1] == (20,)  # type: ignore[attr-defined]

    client.conn.rows = [  # type: ignore[attr-defined]
        {
            "source": "gp-25544",
            "started_at": MINUTE,
            "finished_at": NOW,
            "http_status": 200,
            "rows_received": 1,
            "rows_upserted": 1,
            "rows_rejected": 0,
            "error": None,
        }
    ]
    client.conn.calls.clear()  # type: ignore[attr-defined]
    log = client.get("/api/ingest-log")
    assert log.status_code == 200
    assert log.json()[0]["source"] == "gp-25544"
    assert log.json()[0]["error"] is None
    assert client.conn.calls[0][0] == INGEST_LOG_SQL  # type: ignore[attr-defined]
    assert client.conn.calls[0][1] == (50,)  # type: ignore[attr-defined]

    too_many = client.get("/api/ingest-log", params={"limit": 201})
    assert too_many.status_code == 422


def test_new_series_share_the_window_and_return_rows(client: TestClient) -> None:
    refused = client.get(
        "/api/mag",
        params={"from": "2026-10-01T00:00:00Z", "to": "2026-10-18T00:00:00Z"},
    )
    assert refused.status_code == 422
    assert client.conn.calls == []  # type: ignore[attr-defined]

    client.conn.rows = [  # type: ignore[attr-defined]
        {
            "time_tag": MINUTE,
            "source": "ACE",
            "active": True,
            "bt": 5.0,
            "bx_gse": 1.0,
            "by_gse": 2.0,
            "bz_gse": -3.0,
            "bx_gsm": 1.0,
            "by_gsm": 2.0,
            "bz_gsm": -4.0,
        }
    ]
    mag = client.get("/api/mag")
    assert mag.status_code == 200
    assert mag.json()["processing_level"] == "real-time"
    assert mag.json()["rows"][0]["bz_gsm"] == -4.0
    assert client.conn.calls[-1][0] == MAG_SQL  # type: ignore[attr-defined]

    client.conn.rows = [  # type: ignore[attr-defined]
        {
            "time_tag": MINUTE,
            "satellite": 18,
            "energy": "0.1-0.8nm",
            "flux": 1.2e-6,
            "observed_flux": 1.3e-6,
            "electron_correction": 0.1e-6,
            "electron_contamination": False,
        }
    ]
    goes = client.get(
        "/api/goes-xray",
        params={
            "from": "2026-10-26T00:00:00Z",
            "to": "2026-10-26T05:00:00Z",
            "energy": "0.1-0.8nm",
        },
    )
    assert goes.status_code == 200
    assert goes.json()["rows"][0]["energy"] == "0.1-0.8nm"
    assert client.conn.calls[-1][0] == GOES_SQL  # type: ignore[attr-defined]
    assert client.conn.calls[-1][1][2:] == ("0.1-0.8nm", "0.1-0.8nm", 500)  # type: ignore[attr-defined]

    client.conn.rows = [  # type: ignore[attr-defined]
        {"time_tag": MINUTE, "kp_index": 5, "estimated_kp": 5.0, "kp": "5Z"}
    ]
    one_minute = client.get("/api/kp-1m")
    assert one_minute.status_code == 200
    assert one_minute.json()["rows"][0]["estimated_kp"] == 5.0
    assert client.conn.calls[-1][0] == KP_1M_SQL  # type: ignore[attr-defined]

    client.conn.rows = [  # type: ignore[attr-defined]
        {"time_tag": MINUTE, "kp": 5.33, "a_running": 32, "station_count": 8}
    ]
    three_hour = client.get("/api/kp-3h")
    assert three_hour.status_code == 200
    assert three_hour.json()["rows"][0]["kp"] == 5.33
    assert client.conn.calls[-1][0] == KP_3H_SQL  # type: ignore[attr-defined]

    client.conn.rows = [  # type: ignore[attr-defined]
        {
            "issue_datetime": MINUTE,
            "product_id": "K04A",
            "message": "Space Weather Message Code: ALTK04",
        }
    ]
    alerts = client.get("/api/alerts")
    assert alerts.status_code == 200
    assert alerts.json()["limit"] == 50
    assert alerts.json()["rows"][0]["product_id"] == "K04A"
    assert client.conn.calls[-1][0] == ALERTS_SQL  # type: ignore[attr-defined]

    client.conn.rows = [  # type: ignore[attr-defined]
        {
            "epoch": MINUTE,
            "norad_cat_id": 25544,
            "object_name": "ISS (ZARYA)",
            "object_id": "1998-067A",
            "perigee_altitude_km": 414.8,
            "apogee_altitude_km": 424.2,
        }
    ]
    perigee = client.get("/api/satellite-perigee", params={"norad_cat_id": 25544})
    assert perigee.status_code == 200
    body = perigee.json()
    assert body["altitude"].startswith("two-body")
    assert body["rows"][0]["perigee_altitude_km"] == 414.8
    assert client.conn.calls[-1][0] == PERIGEE_SQL  # type: ignore[attr-defined]
    assert client.conn.calls[-1][1][2:4] == (25544, 25544)  # type: ignore[attr-defined]

    missing = client.get("/api/satellite-perigee", params={"norad_cat_id": 0})
    assert missing.status_code == 422


def test_kp_3h_allows_a_year_and_rejects_a_longer_range(client: TestClient) -> None:
    """The year ring is 365 days of 3-hour rows. Minute routes stay at 7 days."""
    year = client.get(
        "/api/kp-3h",
        params={
            "from": "2025-10-27T00:00:00Z",
            "to": "2026-10-27T00:00:00Z",
            "limit": 3300,
        },
    )
    assert year.status_code == 200
    assert client.conn.calls[-1][0] == KP_3H_SQL  # type: ignore[attr-defined]
    assert client.conn.calls[-1][1][2] == 3300  # type: ignore[attr-defined]

    too_long = client.get(
        "/api/kp-3h",
        params={"from": "2024-01-01T00:00:00Z", "to": "2026-01-01T00:00:00Z"},
    )
    assert too_long.status_code == 422
    too_many = client.get("/api/kp-3h", params={"limit": 3301})
    assert too_many.status_code == 422
    minute = client.get(
        "/api/kp-1m",
        params={"from": "2026-10-01T00:00:00Z", "to": "2026-10-18T00:00:00Z"},
    )
    assert minute.status_code == 422


def test_openapi_lists_the_read_routes(client: TestClient) -> None:
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    assert set(paths) == {
        "/api/health",
        "/api/solar-wind",
        "/api/sources",
        "/api/ingest-log",
        "/api/mag",
        "/api/goes-xray",
        "/api/kp-1m",
        "/api/kp-3h",
        "/api/alerts",
        "/api/satellite-perigee",
    }
    for path in paths:
        assert list(paths[path]) == ["get"]
