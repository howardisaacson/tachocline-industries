"""GOES X-ray flux poller (issue #31). HTTP and Postgres are fakes."""

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

from ti_ingest.__main__ import (
    GOES_JOB_ID,
    JOB_ID,
    add_goes_job,
    build_scheduler,
    execute_goes_job,
)
from ti_ingest.goes_xray import PRODUCT_NAME, PRODUCT_URL, poll_goes_xray, startup_line
from ti_ingest.load import XRAY_UPSERT, store_fetch
from ti_ingest.migrate import DatabaseSettings
from ti_ingest.models import XrayRow
from ti_ingest.swpc import FetchResult, SwpcSettings, make_client

WHEN = datetime(2026, 10, 25, 20, 37, tzinfo=UTC)
MINUTE = datetime(2026, 10, 25, 20, 37, tzinfo=UTC)


def _settings(raw_dir: Path) -> SwpcSettings:
    return SwpcSettings(raw_dir, "TachoclineIndustries/0.1 (test)", 5)


def _database() -> DatabaseSettings:
    return DatabaseSettings("db", 5432, "ti_admin", "not-used", "tachocline")


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return make_client("TachoclineIndustries/0.1 (test)", transport=handler)


def xray_row(
    energy: str = "0.1-0.8nm",
    flux: float | None = 2.9e-7,
    **extra: object,
) -> dict[str, object]:
    """One object shaped like the live file, including the upstream typo."""
    row: dict[str, object] = {
        "time_tag": "2026-10-25T20:37:00Z",
        "satellite": 18,
        "flux": flux,
        "observed_flux": 3.19e-7,
        "electron_correction": 2.87e-8,
        "electron_contaminaton": False,
        "energy": energy,
        "unused": "kept in the raw file only",
    }
    row.update(extra)
    return row


class FakeDB:
    """Commit copies the buffer. Rollback drops it. Key is three columns."""

    def __init__(self) -> None:
        self.tables: dict[tuple[object, object, object], tuple[object, ...]] = {}
        self.logs: list[tuple[object, ...]] = []
        self.statements: list[str] = []
        self._tables: dict[tuple[object, object, object], tuple[object, ...]] = {}
        self._logs: list[tuple[object, ...]] = []
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.tables.update(self._tables)
        self.logs.extend(self._logs)
        self._tables = {}
        self._logs = []

    def rollback(self) -> None:
        self._tables = {}
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
        if "ON CONFLICT (time_tag, satellite, energy) DO UPDATE" not in query:
            raise AssertionError("measurement insert is not an upsert")
        self.db._tables[(params[0], params[1], params[2])] = params

    def executemany(self, query: str, params_seq: list[tuple[object, ...]]) -> None:
        for params in params_seq:
            self.execute(query, params)


def test_startup_line_names_the_landing_zone_and_the_key() -> None:
    message = startup_line("/data/raw", 5)
    assert "every 5 min" in message
    assert "xrays-6-hour" in message
    assert "/data/raw/goes_xray" in message
    assert "(time_tag, satellite, energy)" in message


def test_poll_saves_the_body_unchanged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    body = b'[{"energy": "0.1-0.8nm"}]\n'
    counts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counts["n"] += 1
        assert str(request.url) == PRODUCT_URL
        assert request.headers["user-agent"] == "TachoclineIndustries/0.1 (test)"
        return httpx.Response(200, content=body)

    caplog.set_level(logging.INFO)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_goes_xray(client, tmp_path, now=WHEN)

    assert counts["n"] == 1
    assert results[0].error is None
    path = results[0].path
    assert path is not None
    assert path.parent == tmp_path / "goes_xray" / "2026-10-25"
    assert path.name == "20261025T203700Z_xrays-6-hour.json"
    assert path.read_bytes() == body
    assert not path.with_suffix(".json.partial").exists()
    assert "Landed xrays-6-hour" in caplog.text


def test_client_error_is_logged_and_not_retried(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    counts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counts["n"] += 1
        return httpx.Response(404, content=b"missing")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_goes_xray(client, tmp_path, now=WHEN)

    assert counts["n"] == 1
    assert results[0].status_code == 404
    assert results[0].path is None
    assert results[0].stop_run is False
    assert list(tmp_path.rglob("*")) == []
    assert "HTTP 404" in caplog.text
    assert "not retrying" in caplog.text


def test_too_many_requests_is_not_retried(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    counts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counts["n"] += 1
        return httpx.Response(429, content=b"slow down")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_goes_xray(client, tmp_path, now=WHEN)

    assert counts["n"] == 1
    assert results[0].status_code == 429
    assert results[0].stop_run is True
    assert list(tmp_path.rglob("*")) == []
    assert "not retrying" in caplog.text


def test_model_reads_the_upstream_typo_and_ignores_extra_keys() -> None:
    row = XrayRow.model_validate(xray_row())
    assert row.time_tag == MINUTE
    assert row.satellite == 18
    assert row.energy == "0.1-0.8nm"
    assert row.electron_contamination is False
    assert "unused" not in row.model_dump()
    corrected = xray_row(electron_contamination=True)
    del corrected["electron_contaminaton"]
    assert XrayRow.model_validate(corrected).electron_contamination is True


def test_null_flux_is_kept_and_a_missing_key_is_rejected() -> None:
    kept = XrayRow.model_validate(xray_row(flux=None))
    assert kept.flux is None
    missing = xray_row()
    del missing["flux"]
    with pytest.raises(ValidationError):
        XrayRow.model_validate(missing)


def test_bad_satellite_energy_and_flag_are_rejected() -> None:
    with pytest.raises(ValidationError):
        XrayRow.model_validate(xray_row(satellite="18"))
    with pytest.raises(ValidationError):
        XrayRow.model_validate(xray_row(satellite=0))
    with pytest.raises(ValidationError):
        XrayRow.model_validate(xray_row(energy="  "))
    flagged = xray_row()
    flagged["electron_contaminaton"] = "false"
    with pytest.raises(ValidationError):
        XrayRow.model_validate(flagged)


def test_upsert_sql_uses_the_three_column_key() -> None:
    assert "INSERT INTO goes_xray_flux" in XRAY_UPSERT
    assert "ON CONFLICT (time_tag, satellite, energy) DO UPDATE" in XRAY_UPSERT
    assert "%s" in XRAY_UPSERT
    assert "18" not in XRAY_UPSERT


def test_rerun_updates_the_same_minute_and_keeps_both_bands(tmp_path: Path) -> None:
    path = tmp_path / "xrays.json"
    path.write_bytes(
        json.dumps(
            [xray_row("0.05-0.4nm", 1.0e-8), xray_row("0.1-0.8nm", 2.9e-7)]
        ).encode()
    )
    fetch = FetchResult(PRODUCT_NAME, 200, path, None, False)
    db = FakeDB()
    store_fetch(db, fetch, started_at=WHEN)
    path.write_bytes(json.dumps([xray_row("0.1-0.8nm", 4.0e-6)]).encode())
    store_fetch(db, fetch, started_at=WHEN)

    assert len(db.tables) == 2
    long = db.tables[(MINUTE, 18, "0.1-0.8nm")]
    assert long[3] == 4.0e-6
    assert db.tables[(MINUTE, 18, "0.05-0.4nm")][3] == 1.0e-8
    assert [row[0] for row in db.logs] == ["xrays-6-hour", "xrays-6-hour"]
    assert db.logs[1][5] == 1
    assert XRAY_UPSERT in db.statements


def test_job_lands_raw_then_upserts_and_a_404_does_not(tmp_path: Path) -> None:
    body = json.dumps([xray_row()]).encode()
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        assert request.headers["user-agent"] == "TachoclineIndustries/0.1 (test)"
        if seen["n"] == 1:
            return httpx.Response(200, content=body)
        return httpx.Response(404, content=b"missing")

    db = FakeDB()
    settings = _settings(tmp_path)
    transport = httpx.MockTransport(handler)
    execute_goes_job(
        settings,
        _database(),
        transport=transport,
        connect_fn=lambda _database: db,
        now=WHEN,
    )
    execute_goes_job(
        settings,
        _database(),
        transport=transport,
        connect_fn=lambda _database: db,
        now=WHEN,
    )

    assert seen["n"] == 2
    assert list(db.tables) == [(MINUTE, 18, "0.1-0.8nm")]
    assert [row[3] for row in db.logs] == [200, 404]
    assert db.logs[1][7] == "HTTP 404"
    assert db.closed is True
    assert len(list(tmp_path.rglob("*.json"))) == 1


def test_postgres_outage_still_lands_the_raw_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"[]")

    def boom(_settings: DatabaseSettings) -> FakeDB:
        raise OSError("db down")

    caplog.set_level(logging.ERROR)
    execute_goes_job(
        _settings(tmp_path),
        _database(),
        transport=httpx.MockTransport(handler),
        connect_fn=boom,
        now=WHEN,
    )
    assert len(list(tmp_path.rglob("*.json"))) == 1
    assert "Postgres is unavailable" in caplog.text
    assert "not-used" not in caplog.text


def test_scheduler_registers_xray_beside_solar_wind() -> None:
    scheduler = BlockingScheduler(timezone=UTC)
    job = add_goes_job(scheduler, 5, lambda: None)
    assert job.id == GOES_JOB_ID
    assert job.max_instances == 1
    assert job.coalesce is True
    both = build_scheduler(5, lambda: None, lambda: None)
    assert {item.id for item in both.get_jobs()} == {JOB_ID, GOES_JOB_ID}
