"""Validate and upsert SWPC rows (issue #27).

HTTP is mocked. Postgres is a fake connection: writes stay in a buffer
until ``commit``, and ``rollback`` drops that buffer. A second upsert of
the same ``(time_tag, source)`` replaces the row. Nothing here calls
SWPC or a database server.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import httpx
import pytest
from pydantic import ValidationError

from ti_ingest.__main__ import execute_swpc_job
from ti_ingest.load import INGEST_LOG_SQL, MAG_UPSERT, WIND_UPSERT, store_fetch
from ti_ingest.migrate import DatabaseSettings
from ti_ingest.models import MagRow, WindRow
from ti_ingest.swpc import PRODUCTS, FetchResult, SwpcSettings

WHEN = datetime(2026, 10, 25, 19, 45, tzinfo=UTC)
MINUTE = datetime(2026, 10, 25, 19, 45, tzinfo=UTC)
WIND_URL = PRODUCTS[0].url
MAG_URL = PRODUCTS[1].url


def _database() -> DatabaseSettings:
    return DatabaseSettings("db", 5432, "ti_admin", "not-used", "tachocline")


def _settings(raw_dir: Path) -> SwpcSettings:
    return SwpcSettings(raw_dir, "TachoclineIndustries/0.1 (test)", 5)


def wind_row(source: str, speed: float, **extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "time_tag": "2026-10-25T19:45:00",
        "active": source == "SOLAR1",
        "source": source,
        "proton_speed": speed,
        "proton_density": 3.27,
        "proton_temperature": 63580,
        "alpha_density": None,
    }
    row.update(extra)
    return row


def mag_row(source: str, bz: float) -> dict[str, object]:
    return {
        "time_tag": "2026-10-25T19:45:00",
        "active": source == "SOLAR1",
        "source": source,
        "bt": 3.38,
        "bx_gse": 0.72,
        "by_gse": 3.26,
        "bz_gse": 0.43,
        "bx_gsm": 0.72,
        "by_gsm": 3.29,
        "bz_gsm": bz,
        "phi_gsm": 77.6,
    }


class FakeDB:
    """In-memory stand-in for a psycopg connection.

    Uncommitted rows live in ``_tables``. ``commit`` copies them into
    ``tables``. That is the part of a transaction these tests need: a
    forgotten ``commit`` leaves ``tables`` empty, and ``rollback`` drops
    a write that did not finish.
    """

    def __init__(self, *, fail_upsert: bool = False) -> None:
        self.fail_upsert = fail_upsert
        self.tables: dict[str, dict[tuple[object, object], tuple[object, ...]]] = {
            "solar_wind": {},
            "rtsw_mag_1m": {},
        }
        self.logs: list[tuple[object, ...]] = []
        self.statements: list[str] = []
        self._tables: dict[str, dict[tuple[object, object], tuple[object, ...]]] = {
            "solar_wind": {},
            "rtsw_mag_1m": {},
        }
        self._logs: list[tuple[object, ...]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        for name in self.tables:
            self.tables[name].update(self._tables[name])
        self.logs.extend(self._logs)
        self._clear_pending()
        self.commits += 1

    def rollback(self) -> None:
        self._clear_pending()
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True

    def _clear_pending(self) -> None:
        self._tables = {"solar_wind": {}, "rtsw_mag_1m": {}}
        self._logs = []


class FakeCursor:
    def __init__(self, db: FakeDB) -> None:
        self.db = db

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] = ()) -> None:
        self._apply(query, params)

    def executemany(self, query: str, params_seq: list[tuple[object, ...]]) -> None:
        for params in params_seq:
            self.execute(query, params)

    def _apply(self, query: str, params: tuple[object, ...]) -> None:
        self.db.statements.append(query)
        if "INSERT INTO ingest_log" in query:
            self.db._logs.append(params)
            return
        if "ON CONFLICT (time_tag, source) DO UPDATE" not in query:
            raise AssertionError("measurement insert is not an upsert")
        if "INSERT INTO solar_wind" in query:
            table = "solar_wind"
        elif "INSERT INTO rtsw_mag_1m" in query:
            table = "rtsw_mag_1m"
        else:
            raise AssertionError(query)
        # Write first, then fail, so a missing rollback would publish the row
        # when the error log commits.
        key = (params[0], params[1])
        self.db._tables[table][key] = params
        if self.db.fail_upsert:
            raise RuntimeError("disk full")


def _fetch(path: Path, product: str = "rtsw_wind_1m") -> FetchResult:
    return FetchResult(product, 200, path, None, False)


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_bytes(json.dumps(rows).encode())


def test_wind_model_uses_utc_and_ignores_unused_keys() -> None:
    row = WindRow.model_validate(wind_row("SOLAR1", 341.5))
    assert row.time_tag == MINUTE
    assert row.proton_temperature == 63580.0
    assert "alpha_density" not in row.model_dump()
    zulu = wind_row("ACE", 400.0, time_tag="2026-10-25T19:45:00Z")
    assert WindRow.model_validate(zulu).time_tag == MINUTE


def test_null_measurement_is_kept_and_a_missing_key_is_rejected() -> None:
    kept = WindRow.model_validate(wind_row("ACE", 1.0, proton_speed=None))
    assert kept.proton_speed is None
    missing = wind_row("ACE", 1.0)
    del missing["proton_density"]
    with pytest.raises(ValidationError):
        WindRow.model_validate(missing)


def test_blank_source_and_non_bool_active_are_rejected() -> None:
    with pytest.raises(ValidationError):
        WindRow.model_validate(wind_row("   ", 1.0))
    with pytest.raises(ValidationError):
        WindRow.model_validate(wind_row("ACE", 1.0, active="true"))


def test_mag_model_keeps_the_stored_components() -> None:
    row = MagRow.model_validate(mag_row("IMAP", -0.23))
    assert row.as_params()[9] == -0.23
    assert len(row.as_params()) == 10


def test_upsert_sql_targets_time_tag_and_source() -> None:
    for statement in (WIND_UPSERT, MAG_UPSERT):
        assert "ON CONFLICT (time_tag, source) DO UPDATE" in statement
        assert "%s" in statement
        assert "SOLAR1" not in statement
    assert "INSERT INTO solar_wind" in WIND_UPSERT
    assert "INSERT INTO rtsw_mag_1m" in MAG_UPSERT


def test_rerun_of_the_same_raw_file_does_not_insert_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "rtsw_wind_1m.json"
    original = [wind_row("SOLAR1", 341.5), wind_row("ACE", 400.0)]
    _write(path, original)
    db = FakeDB()
    fetch = _fetch(path)
    store_fetch(db, fetch, started_at=WHEN)
    store_fetch(db, fetch, started_at=WHEN)

    assert set(db.tables["solar_wind"]) == {(MINUTE, "SOLAR1"), (MINUTE, "ACE")}
    assert len(db.tables["solar_wind"]) == 2
    assert len(db.logs) == 2
    assert db.logs[0][0] == "rtsw_wind_1m"
    assert db.logs[0][3] == 200
    assert db.logs[0][4] == 2  # rows_received
    assert db.logs[0][5] == 2  # rows_upserted
    assert db.logs[0][6] == 0  # rows_rejected
    assert db.logs[0][7] is None
    assert db.commits == 2
    assert path.read_bytes() == json.dumps(original).encode()
    assert all("not-used" not in sql for sql in db.statements)
    assert WIND_UPSERT in db.statements

    _write(path, [wind_row("SOLAR1", 999.0), wind_row("ACE", 400.0)])
    store_fetch(db, fetch, started_at=WHEN)
    assert len(db.tables["solar_wind"]) == 2
    assert db.tables["solar_wind"][(MINUTE, "SOLAR1")][3] == 999.0
    assert len(db.logs) == 3


def test_duplicate_key_inside_one_file_collapses_to_one_row(tmp_path: Path) -> None:
    path = tmp_path / "rtsw_wind_1m.json"
    _write(path, [wind_row("SOLAR1", 1.0), wind_row("SOLAR1", 2.0)])
    db = FakeDB()
    store_fetch(db, _fetch(path), started_at=WHEN)
    assert len(db.tables["solar_wind"]) == 1
    assert db.tables["solar_wind"][(MINUTE, "SOLAR1")][3] == 2.0
    assert db.logs[0][4:] == (2, 2, 0, None)


def test_invalid_row_is_counted_and_not_stored(tmp_path: Path) -> None:
    path = tmp_path / "rtsw_wind_1m.json"
    bad = {
        "time_tag": "not-a-time",
        "source": "ACE",
        "active": True,
        "proton_speed": 1,
        "proton_density": 1,
        "proton_temperature": 1,
    }
    _write(path, [wind_row("SOLAR1", 341.5), bad])
    db = FakeDB()
    store_fetch(db, _fetch(path), started_at=WHEN)
    assert list(db.tables["solar_wind"]) == [(MINUTE, "SOLAR1")]
    assert db.logs[0][4:] == (2, 1, 1, None)


def test_unreadable_json_logs_an_error_and_upserts_nothing(tmp_path: Path) -> None:
    path = tmp_path / "rtsw_wind_1m.json"
    path.write_bytes(b"{not json")
    db = FakeDB()
    store_fetch(db, _fetch(path), started_at=WHEN)
    assert db.tables["solar_wind"] == {}
    assert db.logs[0][4] == 0
    assert db.logs[0][5] == 0
    assert str(db.logs[0][7]).startswith("JSONDecodeError")

    path.write_bytes(b'{"time_tag": "2026-10-25T19:45:00"}')
    store_fetch(db, _fetch(path), started_at=WHEN)
    assert db.logs[1][7] == "SWPC body is not a JSON array"
    assert db.tables["solar_wind"] == {}


def test_http_failure_still_writes_ingest_log() -> None:
    db = FakeDB()
    fetch = FetchResult("rtsw_wind_1m", 404, None, "HTTP 404", False)
    store_fetch(db, fetch, started_at=WHEN)
    assert db.tables["solar_wind"] == {}
    assert db.logs[0][3] == 404
    assert db.logs[0][4:] == (0, 0, 0, "HTTP 404")
    assert db.statements == [INGEST_LOG_SQL]


def test_upsert_error_rolls_back_and_logs(tmp_path: Path) -> None:
    path = tmp_path / "rtsw_wind_1m.json"
    _write(path, [wind_row("SOLAR1", 341.5)])
    db = FakeDB(fail_upsert=True)
    store_fetch(db, _fetch(path), started_at=WHEN)
    assert db.tables["solar_wind"] == {}
    assert db.rollbacks >= 1
    assert db.logs[0][5] == 0
    assert str(db.logs[0][7]).startswith("RuntimeError")


def test_scheduled_run_upserts_both_files_and_a_rerun_adds_no_rows(
    tmp_path: Path,
) -> None:
    wind_body = json.dumps([wind_row("SOLAR1", 341.5), wind_row("ACE", 400.0)]).encode()
    mag_body = json.dumps([mag_row("SOLAR1", -1.5)]).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == WIND_URL:
            return httpx.Response(200, content=wind_body)
        if str(request.url) == MAG_URL:
            return httpx.Response(200, content=mag_body)
        raise AssertionError(f"unexpected URL {request.url}")

    db = FakeDB()
    settings = _settings(tmp_path)
    transport = httpx.MockTransport(handler)
    execute_swpc_job(
        settings,
        _database(),
        transport=transport,
        connect_fn=lambda _database: db,
        now=WHEN,
    )
    execute_swpc_job(
        settings,
        _database(),
        transport=transport,
        connect_fn=lambda _database: db,
        now=WHEN,
    )

    assert len(db.tables["solar_wind"]) == 2
    assert list(db.tables["rtsw_mag_1m"]) == [(MINUTE, "SOLAR1")]
    assert db.tables["rtsw_mag_1m"][(MINUTE, "SOLAR1")][9] == -1.5
    assert [row[0] for row in db.logs] == [
        "rtsw_wind_1m",
        "rtsw_mag_1m",
        "rtsw_wind_1m",
        "rtsw_mag_1m",
    ]
    assert db.closed is True
    assert len(list(tmp_path.rglob("*.json"))) == 2
    assert MAG_UPSERT in db.statements


def test_rate_limit_logs_only_the_file_that_was_fetched(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == MAG_URL:
            raise AssertionError("429 on wind must skip mag")
        return httpx.Response(429, content=b"slow down")

    db = FakeDB()
    caplog.set_level(logging.ERROR)
    execute_swpc_job(
        _settings(tmp_path),
        _database(),
        transport=httpx.MockTransport(handler),
        connect_fn=lambda _database: db,
        now=WHEN,
    )
    assert len(db.logs) == 1
    assert db.logs[0][0] == "rtsw_wind_1m"
    assert db.logs[0][3] == 429
    assert db.logs[0][7] == "HTTP 429"
    assert db.tables["solar_wind"] == {}
    assert db.tables["rtsw_mag_1m"] == {}


def test_postgres_outage_still_lands_the_raw_files(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"[]")

    def boom(_settings: DatabaseSettings) -> FakeDB:
        raise OSError("db down")

    caplog.set_level(logging.ERROR)
    execute_swpc_job(
        _settings(tmp_path),
        _database(),
        transport=httpx.MockTransport(handler),
        connect_fn=boom,
        now=WHEN,
    )
    assert len(list(tmp_path.rglob("*.json"))) == 2
    assert "Postgres is unavailable" in caplog.text
    assert "not-used" not in caplog.text
