"""Kp index and SWPC alerts poller (issue #32). HTTP and Postgres are fakes."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import httpx
import pytest
from apscheduler.schedulers.blocking import BlockingScheduler
from pydantic import ValidationError

from ti_ingest.__main__ import KP_JOB_ID, add_kp_job, execute_kp_job
from ti_ingest.kp_alerts import PRODUCTS, poll_kp_alerts, startup_line
from ti_ingest.load import ALERT_UPSERT, KP_1M_UPSERT, KP_3H_UPSERT, store_fetch
from ti_ingest.migrate import DatabaseSettings
from ti_ingest.models import AlertRow, Kp1mRow, Kp3hRow
from ti_ingest.swpc import FetchResult, SwpcSettings, make_client

WHEN = datetime(2026, 10, 25, 20, 37, tzinfo=UTC)
MINUTE = datetime(2026, 10, 25, 21, 26, tzinfo=UTC)
BLOCK = datetime(2026, 10, 19, 0, 0, tzinfo=UTC)
ISSUED = datetime(2026, 10, 25, 9, 27, 50, 723000, tzinfo=UTC)


def _settings(raw_dir: Path) -> SwpcSettings:
    return SwpcSettings(raw_dir, "TachoclineIndustries/0.1 (test)", 5)


def _database() -> DatabaseSettings:
    return DatabaseSettings("db", 5432, "ti_admin", "not-used", "tachocline")


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return make_client("TachoclineIndustries/0.1 (test)", transport=handler)


def kp_1m_row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "time_tag": "2026-10-25T21:26:00",
        "kp_index": 0,
        "estimated_kp": 0.33,
        "kp": "0P",
        "unused": "kept in the raw file only",
    }
    row.update(extra)
    return row


def kp_3h_row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "time_tag": "2026-10-19T00:00:00",
        "Kp": 0.33,
        "a_running": 2,
        "station_count": 8,
        "unused": "kept in the raw file only",
    }
    row.update(extra)
    return row


def alert_row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "product_id": "K04A",
        "issue_datetime": "2026-10-25 09:27:50.723",
        "message": "Space Weather Message Code: ALTK04\r\nSerial Number: 1",
        "unused": "kept in the raw file only",
    }
    row.update(extra)
    return row


class FakeDB:
    """Commit copies the buffer. Rollback drops it."""

    def __init__(self) -> None:
        self.rows: dict[tuple[object, ...], tuple[object, ...]] = {}
        self.logs: list[tuple[object, ...]] = []
        self.statements: list[str] = []
        self._rows: dict[tuple[object, ...], tuple[object, ...]] = {}
        self._logs: list[tuple[object, ...]] = []
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.rows.update(self._rows)
        self.logs.extend(self._logs)
        self._rows = {}
        self._logs = []

    def rollback(self) -> None:
        self._rows = {}
        self._logs = []

    def close(self) -> None:
        self.closed = True


class FakeCursor:
    def __init__(self, db: FakeDB) -> None:
        self.db = db

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] = ()) -> None:
        self.db.statements.append(query)
        if "INSERT INTO ingest_log" in query:
            self.db._logs.append(params)
            return
        if "ON CONFLICT" not in query:
            raise AssertionError("measurement insert is not an upsert")
        if "INSERT INTO planetary_kp_1m" in query:
            self.db._rows[("1m", params[0])] = params
            return
        if "INSERT INTO planetary_kp_3h" in query:
            self.db._rows[("3h", params[0])] = params
            return
        if "INSERT INTO swpc_alert" in query:
            self.db._rows[("alert", params[0], params[1])] = params
            return
        raise AssertionError(query)

    def executemany(self, query: str, params_seq: list[tuple[object, ...]]) -> None:
        for params in params_seq:
            self.execute(query, params)


def test_startup_line_names_the_landing_zone_and_the_keys() -> None:
    message = startup_line("/data/raw", 5)
    assert "every 5 min" in message
    assert "planetary_k_index_1m" in message
    assert "noaa-planetary-k-index" in message
    assert "alerts" in message
    assert "/data/raw/swpc_kp" in message
    assert "time_tag" in message
    assert "(issue_datetime, product_id)" in message


def test_poll_saves_each_body_unchanged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bodies = {
        PRODUCTS[0].url: b'[{"estimated_kp": 0.33}]\n',
        PRODUCTS[1].url: b'[{"Kp": 1.0}]\n',
        PRODUCTS[2].url: b'[{"product_id": "K04A"}]\n',
    }
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.headers["user-agent"] == "TachoclineIndustries/0.1 (test)"
        return httpx.Response(200, content=bodies[str(request.url)])

    caplog.set_level(logging.INFO)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_kp_alerts(client, tmp_path, now=WHEN)

    assert seen == [product.url for product in PRODUCTS]
    assert [item.error for item in results] == [None, None, None]
    expected = [
        "20261025T203700Z_planetary_k_index_1m.json",
        "20261025T203700Z_noaa-planetary-k-index.json",
        "20261025T203700Z_alerts.json",
    ]
    for result, name, url in zip(results, expected, bodies, strict=True):
        path = result.path
        assert path is not None
        assert path.parent == tmp_path / "swpc_kp" / "2026-10-25"
        assert path.name == name
        assert path.read_bytes() == bodies[url]
        assert not path.with_suffix(".json.partial").exists()
    assert "Landed planetary_k_index_1m" in caplog.text


def test_client_error_is_logged_and_the_other_files_still_fetch(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url) == PRODUCTS[0].url:
            return httpx.Response(404, content=b"missing")
        return httpx.Response(200, content=b"[]")

    with _client(httpx.MockTransport(handler)) as client:
        results = poll_kp_alerts(client, tmp_path, now=WHEN)

    assert seen == [product.url for product in PRODUCTS]
    assert results[0].status_code == 404
    assert results[0].path is None
    assert results[0].stop_run is False
    assert results[1].path is not None
    assert results[2].path is not None
    names = sorted(path.name for path in tmp_path.rglob("*.json"))
    assert names == [
        "20261025T203700Z_alerts.json",
        "20261025T203700Z_noaa-planetary-k-index.json",
    ]


def test_too_many_requests_skips_the_remaining_files(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(429, content=b"slow down")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_kp_alerts(client, tmp_path, now=WHEN)

    assert seen == [PRODUCTS[0].url]
    assert results[0].status_code == 429
    assert results[0].stop_run is True
    assert len(results) == 1
    assert list(tmp_path.rglob("*")) == []
    assert "not retrying" in caplog.text
    assert "skipping the other files" in caplog.text


def test_models_read_the_live_keys_and_ignore_extras() -> None:
    one_minute = Kp1mRow.model_validate(kp_1m_row())
    assert one_minute.time_tag == MINUTE
    assert one_minute.estimated_kp == 0.33
    assert one_minute.kp == "0P"
    assert "unused" not in one_minute.model_dump()

    three_hour = Kp3hRow.model_validate(kp_3h_row())
    assert three_hour.time_tag == BLOCK
    assert three_hour.kp == 0.33
    assert three_hour.station_count == 8

    alert = AlertRow.model_validate(alert_row())
    assert alert.issue_datetime == ISSUED
    assert alert.product_id == "K04A"
    assert alert.message is not None
    assert "ALTK04" in alert.message


def test_null_measurement_is_kept_and_a_missing_key_is_rejected() -> None:
    kept = Kp1mRow.model_validate(kp_1m_row(estimated_kp=None))
    assert kept.estimated_kp is None
    missing = kp_1m_row()
    del missing["estimated_kp"]
    with pytest.raises(ValidationError):
        Kp1mRow.model_validate(missing)
    blank = alert_row(product_id="  ")
    with pytest.raises(ValidationError):
        AlertRow.model_validate(blank)
    with pytest.raises(ValidationError):
        Kp3hRow.model_validate(kp_3h_row(station_count="8"))


def test_upsert_sql_uses_the_natural_keys() -> None:
    assert "ON CONFLICT (time_tag) DO UPDATE" in KP_1M_UPSERT
    assert "ON CONFLICT (time_tag) DO UPDATE" in KP_3H_UPSERT
    assert "ON CONFLICT (issue_datetime, product_id) DO UPDATE" in ALERT_UPSERT
    assert "INSERT INTO planetary_kp_1m" in KP_1M_UPSERT
    assert "INSERT INTO swpc_alert" in ALERT_UPSERT


def test_rerun_updates_the_same_minute_and_the_same_alert(tmp_path: Path) -> None:
    kp_path = tmp_path / "kp.json"
    alert_path = tmp_path / "alerts.json"
    kp_path.write_bytes(json.dumps([kp_1m_row()]).encode())
    alert_path.write_bytes(json.dumps([alert_row()]).encode())
    db = FakeDB()
    store_fetch(
        db,
        FetchResult("planetary_k_index_1m", 200, kp_path, None, False),
        started_at=WHEN,
    )
    store_fetch(
        db,
        FetchResult("alerts", 200, alert_path, None, False),
        started_at=WHEN,
    )
    kp_path.write_bytes(json.dumps([kp_1m_row(estimated_kp=1.67)]).encode())
    alert_path.write_bytes(json.dumps([alert_row(message="updated")]).encode())
    store_fetch(
        db,
        FetchResult("planetary_k_index_1m", 200, kp_path, None, False),
        started_at=WHEN,
    )
    store_fetch(
        db,
        FetchResult("alerts", 200, alert_path, None, False),
        started_at=WHEN,
    )

    assert len(db.rows) == 2
    assert db.rows[("1m", MINUTE)][2] == 1.67
    assert db.rows[("alert", ISSUED, "K04A")][2] == "updated"
    assert [row[0] for row in db.logs].count("planetary_k_index_1m") == 2
    assert KP_1M_UPSERT in db.statements
    assert ALERT_UPSERT in db.statements


def test_three_hour_file_uses_the_capital_kp_key(tmp_path: Path) -> None:
    path = tmp_path / "kp3.json"
    path.write_bytes(json.dumps([kp_3h_row()]).encode())
    db = FakeDB()
    store_fetch(
        db,
        FetchResult("noaa-planetary-k-index", 200, path, None, False),
        started_at=WHEN,
    )
    assert db.rows[("3h", BLOCK)][1] == 0.33
    assert db.logs[0][0] == "noaa-planetary-k-index"
    assert db.logs[0][5] == 1
    assert KP_3H_UPSERT in db.statements


def test_job_lands_raw_then_upserts_and_a_404_does_not(tmp_path: Path) -> None:
    bodies = {
        PRODUCTS[0].url: json.dumps([kp_1m_row()]).encode(),
        PRODUCTS[1].url: json.dumps([kp_3h_row()]).encode(),
        PRODUCTS[2].url: json.dumps([alert_row()]).encode(),
    }
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        assert request.headers["user-agent"] == "TachoclineIndustries/0.1 (test)"
        if seen["n"] <= 3:
            return httpx.Response(200, content=bodies[str(request.url)])
        return httpx.Response(404, content=b"missing")

    db = FakeDB()
    transport = httpx.MockTransport(handler)
    execute_kp_job(
        _settings(tmp_path),
        _database(),
        transport=transport,
        connect_fn=lambda _database: db,
        now=WHEN,
    )
    execute_kp_job(
        _settings(tmp_path),
        _database(),
        transport=transport,
        connect_fn=lambda _database: db,
        now=WHEN,
    )

    assert seen["n"] == 6
    assert ("1m", MINUTE) in db.rows
    assert ("3h", BLOCK) in db.rows
    assert ("alert", ISSUED, "K04A") in db.rows
    assert [row[3] for row in db.logs] == [200, 200, 200, 404, 404, 404]
    assert db.logs[3][7] == "HTTP 404"
    assert db.closed is True
    assert len(list(tmp_path.rglob("*.json"))) == 3


def test_postgres_outage_still_lands_the_raw_files(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"[]")

    def boom(_settings: DatabaseSettings) -> FakeDB:
        raise OSError("db down")

    caplog.set_level(logging.ERROR)
    execute_kp_job(
        _settings(tmp_path),
        _database(),
        transport=httpx.MockTransport(handler),
        connect_fn=boom,
        now=WHEN,
    )
    assert len(list(tmp_path.rglob("*.json"))) == 3
    assert "Postgres is unavailable" in caplog.text
    assert "not-used" not in caplog.text


def test_scheduler_registers_the_kp_job() -> None:
    scheduler = BlockingScheduler(timezone=UTC)
    job = add_kp_job(scheduler, 5, lambda: None)
    assert job.id == KP_JOB_ID
    assert job.max_instances == 1
    assert job.coalesce is True
