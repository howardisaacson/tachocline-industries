"""CelesTrak GP poller and derived altitude (issue #34). HTTP and Postgres are fakes."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Self

import httpx
import pytest
from apscheduler.schedulers.blocking import BlockingScheduler
from pydantic import ValidationError

from ti_ingest.__main__ import (
    CELESTRAK_JOB_ID,
    add_celestrak_job,
    execute_celestrak_job,
)
from ti_ingest.celestrak_gp import (
    CATALOG_NUMBERS,
    POLL_MINUTES,
    PRODUCTS,
    poll_celestrak_gp,
    startup_line,
)
from ti_ingest.elements import altitudes_km
from ti_ingest.load import GP_UPSERT, store_fetch
from ti_ingest.migrate import DatabaseSettings
from ti_ingest.models import GpRow
from ti_ingest.swpc import FetchResult, SwpcSettings, make_client

WHEN = datetime(2026, 10, 25, 22, 4, tzinfo=UTC)
EPOCH = datetime(2026, 10, 25, 15, 4, 58, 336608, tzinfo=UTC)

# Two-body results for μ = 398600.0 km³/s² and R = 6378.137 km, computed
# outside altitudes_km and written here as literals. See elements.py.
CIRCULAR_16_REV_KM = 274.416243
ISS_PERIGEE_KM = 414.802660
ISS_APOGEE_KM = 424.187335
ECCENTRIC_PERIGEE_KM = 207.890711
ECCENTRIC_APOGEE_KM = 340.941776


def _settings(raw_dir: Path) -> SwpcSettings:
    return SwpcSettings(raw_dir, "TachoclineIndustries/0.1 (test)", 5)


def _database() -> DatabaseSettings:
    return DatabaseSettings("db", 5432, "ti_admin", "not-used", "tachocline")


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return make_client("TachoclineIndustries/0.1 (test)", transport=handler)


def gp_row(**extra: object) -> dict[str, object]:
    """ISS-shaped OMM object. Mean motion and eccentricity are the known case."""
    row: dict[str, object] = {
        "OBJECT_NAME": "ISS (ZARYA)",
        "OBJECT_ID": "1998-067A",
        "EPOCH": "2026-10-25T15:04:58.336608",
        "MEAN_MOTION": 15.49052179,
        "ECCENTRICITY": 0.00069029,
        "INCLINATION": 51.6336,
        "RA_OF_ASC_NODE": 150.0,
        "ARG_OF_PERICENTER": 80.0,
        "MEAN_ANOMALY": 280.0,
        "EPHEMERIS_TYPE": 0,
        "CLASSIFICATION_TYPE": "U",
        "NORAD_CAT_ID": 25544,
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 1,
        "BSTAR": 0.00012345,
        "MEAN_MOTION_DOT": 0.0001,
        "MEAN_MOTION_DDOT": 0.0,
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
        if "INSERT INTO satellite_gp" in query:
            self.db._rows[(params[0], params[1])] = params
            return
        raise AssertionError(query)

    def executemany(self, query: str, params_seq: list[tuple[object, ...]]) -> None:
        for params in params_seq:
            self.execute(query, params)


def test_circular_and_eccentric_altitudes_match_the_known_kilometers() -> None:
    circular = altitudes_km(16.0, 0.0)
    assert circular[0] == pytest.approx(CIRCULAR_16_REV_KM, abs=1e-6)
    assert circular[1] == pytest.approx(CIRCULAR_16_REV_KM, abs=1e-6)
    perigee, apogee = altitudes_km(16.0, 0.01)
    assert perigee == pytest.approx(ECCENTRIC_PERIGEE_KM, abs=1e-6)
    assert apogee == pytest.approx(ECCENTRIC_APOGEE_KM, abs=1e-6)
    assert perigee < apogee


def test_iss_elements_match_the_known_altitudes() -> None:
    row = GpRow.model_validate(gp_row())
    assert row.epoch == EPOCH
    assert row.norad_cat_id == 25544
    assert row.object_name == "ISS (ZARYA)"
    assert "unused" not in row.model_dump()
    perigee, apogee = row.as_params()[-2:]
    assert perigee == pytest.approx(ISS_PERIGEE_KM, abs=1e-6)
    assert apogee == pytest.approx(ISS_APOGEE_KM, abs=1e-6)


def test_bad_elements_are_rejected() -> None:
    with pytest.raises(ValueError, match="mean motion"):
        altitudes_km(0.0, 0.0)
    with pytest.raises(ValueError, match="eccentricity"):
        altitudes_km(16.0, 1.0)
    with pytest.raises(ValidationError):
        GpRow.model_validate(gp_row(MEAN_MOTION=0))
    with pytest.raises(ValidationError):
        GpRow.model_validate(gp_row(ECCENTRICITY=1))
    missing = gp_row()
    del missing["EPOCH"]
    with pytest.raises(ValidationError):
        GpRow.model_validate(missing)
    with pytest.raises(ValidationError):
        GpRow.model_validate(gp_row(OBJECT_NAME="  "))


def test_startup_line_names_the_two_hour_cadence_and_the_catalog() -> None:
    message = startup_line("/data/raw")
    assert f"every {POLL_MINUTES} min" in message
    assert POLL_MINUTES == 120
    for catnr in CATALOG_NUMBERS:
        assert str(catnr) in message
    assert "/data/raw/celestrak_gp" in message
    assert "(epoch, norad_cat_id)" in message


def test_poll_saves_each_body_unchanged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bodies = {
        product.url: f'[{{"NORAD_CAT_ID": {product.name.removeprefix("gp-")}}}]\n'.encode()
        for product in PRODUCTS
    }
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.headers["user-agent"] == "TachoclineIndustries/0.1 (test)"
        return httpx.Response(200, content=bodies[str(request.url)])

    caplog.set_level(logging.INFO)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_celestrak_gp(client, tmp_path, now=WHEN)

    assert seen == [product.url for product in PRODUCTS]
    assert len(seen) == 5
    assert [item.error for item in results] == [None, None, None, None, None]
    for result, product in zip(results, PRODUCTS, strict=True):
        path = result.path
        assert path is not None
        assert path.parent == tmp_path / "celestrak_gp" / "2026-10-25"
        assert path.name == f"20261025T220400Z_{product.name}.json"
        assert path.read_bytes() == bodies[product.url]
        assert "CATNR=" in product.url
        assert "FORMAT=json" in product.url
        assert "GROUP=" not in product.url
    assert "Landed gp-25544" in caplog.text


def test_client_error_is_logged_and_the_other_catalog_numbers_still_fetch(
    tmp_path: Path,
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url) == PRODUCTS[0].url:
            return httpx.Response(404, content=b"missing")
        return httpx.Response(200, content=b"[]")

    with _client(httpx.MockTransport(handler)) as client:
        results = poll_celestrak_gp(client, tmp_path, now=WHEN)

    assert seen == [product.url for product in PRODUCTS]
    assert results[0].status_code == 404
    assert results[0].path is None
    assert results[0].stop_run is False
    assert results[1].path is not None
    assert len(list(tmp_path.rglob("*.json"))) == 4


def test_too_many_requests_skips_the_remaining_catalog_numbers(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(429, content=b"slow down")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_celestrak_gp(client, tmp_path, now=WHEN)

    assert seen == [PRODUCTS[0].url]
    assert results[0].status_code == 429
    assert results[0].stop_run is True
    assert len(results) == 1
    assert list(tmp_path.rglob("*")) == []
    assert "not retrying" in caplog.text
    assert "skipping the other catalog numbers" in caplog.text


def test_upsert_sql_uses_epoch_and_catalog_number() -> None:
    assert "ON CONFLICT (epoch, norad_cat_id) DO UPDATE" in GP_UPSERT
    assert "INSERT INTO satellite_gp" in GP_UPSERT
    assert "perigee_altitude_km" in GP_UPSERT


def test_rerun_updates_the_same_epoch(tmp_path: Path) -> None:
    path = tmp_path / "gp.json"
    path.write_bytes(json.dumps([gp_row()]).encode())
    db = FakeDB()
    store_fetch(
        db,
        FetchResult("gp-25544", 200, path, None, False),
        started_at=WHEN,
    )
    path.write_bytes(json.dumps([gp_row(OBJECT_NAME="ISS (ZARYA) updated")]).encode())
    store_fetch(
        db,
        FetchResult("gp-25544", 200, path, None, False),
        started_at=WHEN,
    )

    assert len(db.rows) == 1
    stored = db.rows[(EPOCH, 25544)]
    assert stored[2] == "ISS (ZARYA) updated"
    assert stored[-2] == pytest.approx(ISS_PERIGEE_KM, abs=1e-6)
    assert stored[-1] == pytest.approx(ISS_APOGEE_KM, abs=1e-6)
    assert [row[0] for row in db.logs].count("gp-25544") == 2
    assert GP_UPSERT in db.statements


def test_job_lands_raw_then_upserts_and_a_404_does_not(tmp_path: Path) -> None:
    body = json.dumps([gp_row()]).encode()
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        assert request.headers["user-agent"] == "TachoclineIndustries/0.1 (test)"
        if "CATNR=25544" in str(request.url) and seen["n"] <= 5:
            return httpx.Response(200, content=body)
        if seen["n"] <= 5:
            return httpx.Response(200, content=b"[]")
        return httpx.Response(404, content=b"missing")

    db = FakeDB()
    execute_celestrak_job(
        _settings(tmp_path),
        _database(),
        transport=httpx.MockTransport(handler),
        connect_fn=lambda _database: db,
        now=WHEN,
    )
    execute_celestrak_job(
        _settings(tmp_path),
        _database(),
        transport=httpx.MockTransport(handler),
        connect_fn=lambda _database: db,
        now=WHEN,
    )

    assert seen["n"] == 10
    assert (EPOCH, 25544) in db.rows
    assert db.logs[0][0] == "gp-25544"
    assert db.logs[0][5] == 1
    assert [row[3] for row in db.logs][5:] == [404, 404, 404, 404, 404]
    assert db.closed is True
    assert len(list(tmp_path.rglob("*.json"))) == 5


def test_postgres_outage_still_lands_the_raw_files(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"[]")

    def boom(_settings: DatabaseSettings) -> FakeDB:
        raise OSError("db down")

    caplog.set_level(logging.ERROR)
    execute_celestrak_job(
        _settings(tmp_path),
        _database(),
        transport=httpx.MockTransport(handler),
        connect_fn=boom,
        now=WHEN,
    )
    assert len(list(tmp_path.rglob("*.json"))) == 5
    assert "Postgres is unavailable" in caplog.text
    assert "not-used" not in caplog.text


def test_scheduler_registers_a_two_hour_job() -> None:
    scheduler = BlockingScheduler(timezone=UTC)
    job = add_celestrak_job(scheduler, lambda: None)
    assert job.id == CELESTRAK_JOB_ID
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.trigger.interval == timedelta(minutes=120)
