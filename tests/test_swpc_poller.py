"""SWPC poller (issue #26). HTTP is mocked. Nothing here calls SWPC."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from apscheduler.schedulers.blocking import BlockingScheduler

from ti_ingest.__main__ import JOB_ID, add_swpc_job
from ti_ingest.swpc import (
    HTTP_TIMEOUT,
    SwpcConfigError,
    SwpcSettings,
    landing_path,
    make_client,
    poll_swpc,
)

WIND = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
MAG = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
WHEN = datetime(2026, 10, 25, 19, 45, 12, tzinfo=UTC)


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return make_client("TachoclineIndustries/0.1 (test)", transport=handler)


def test_landing_path_uses_utc_date_and_product() -> None:
    # 01:30 at UTC+2 is 23:30 the previous evening in UTC, so the folder
    # date follows UTC, not the machine's local clock.
    local = datetime(2026, 10, 26, 1, 30, 0, tzinfo=timezone(timedelta(hours=2)))
    path = landing_path(Path("/data/raw"), local, "rtsw_wind_1m")
    assert path == Path(
        "/data/raw/swpc_rtsw/2026-10-25/20261025T233000Z_rtsw_wind_1m.json"
    )


def test_landing_path_rejects_a_naive_clock() -> None:
    with pytest.raises(ValueError):
        landing_path(Path("/data/raw"), datetime(2026, 10, 25, 12, 0, 0), "rtsw_mag_1m")


def test_client_sends_user_agent_and_timeout() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["user-agent"] = request.headers["user-agent"]
        seen["accept"] = request.headers["accept"]
        return httpx.Response(200, content=b"[]")

    with _client(httpx.MockTransport(handler)) as client:
        assert client.timeout == HTTP_TIMEOUT
        client.get(WIND)

    assert seen["user-agent"] == "TachoclineIndustries/0.1 (test)"
    assert seen["accept"] == "application/json"


def test_poll_saves_both_bodies_unchanged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    wind_body = b'  [{"time_tag": "2026-10-25T19:45:00"}]\n'
    mag_body = b"not-parsed-yet"
    counts = {"wind": 0, "mag": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == WIND:
            counts["wind"] += 1
            return httpx.Response(200, content=wind_body)
        if str(request.url) == MAG:
            counts["mag"] += 1
            return httpx.Response(200, content=mag_body)
        raise AssertionError(f"unexpected URL {request.url}")

    caplog.set_level(logging.INFO)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_swpc(client, tmp_path, now=WHEN)

    assert counts == {"wind": 1, "mag": 1}
    assert [item.error for item in results] == [None, None]
    wind_path, mag_path = (item.path for item in results)
    assert wind_path is not None and mag_path is not None
    assert wind_path.parent == tmp_path / "swpc_rtsw" / "2026-10-25"
    assert wind_path.name == "20261025T194512Z_rtsw_wind_1m.json"
    assert mag_path.name == "20261025T194512Z_rtsw_mag_1m.json"
    assert wind_path.read_bytes() == wind_body
    assert mag_path.read_bytes() == mag_body
    assert not wind_path.with_suffix(".json.partial").exists()
    assert "Landed rtsw_wind_1m" in caplog.text
    assert "Landed rtsw_mag_1m" in caplog.text


def test_client_error_is_logged_and_not_retried(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    counts = {"wind": 0, "mag": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == WIND:
            counts["wind"] += 1
            return httpx.Response(404, content=b"missing")
        counts["mag"] += 1
        return httpx.Response(200, content=b"[]")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_swpc(client, tmp_path, now=WHEN)

    assert counts == {"wind": 1, "mag": 1}
    assert results[0].status_code == 404
    assert results[0].path is None
    assert results[0].stop_run is False
    assert results[1].path is not None
    assert list(tmp_path.rglob("*.json")) == [results[1].path]
    assert "HTTP 404" in caplog.text
    assert "not retrying" in caplog.text
    assert b"missing" not in results[1].path.read_bytes()


def test_too_many_requests_skips_the_rest_of_the_run(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == MAG:
            raise AssertionError("429 on wind must skip mag")
        return httpx.Response(429, content=b"slow down")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_swpc(client, tmp_path, now=WHEN)

    assert len(results) == 1
    assert results[0].status_code == 429
    assert results[0].stop_run is True
    assert list(tmp_path.rglob("*")) == []
    assert "HTTP 429" in caplog.text
    assert "skipping the other files" in caplog.text


def test_server_error_is_not_retried(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    counts = {"wind": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == WIND:
            counts["wind"] += 1
            return httpx.Response(503, content=b"down")
        return httpx.Response(200, content=b"[]")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_swpc(client, tmp_path, now=WHEN)

    assert counts["wind"] == 1
    assert results[0].status_code == 503
    assert results[0].path is None
    assert results[1].path is not None
    assert "HTTP 503" in caplog.text
    assert "next try is the scheduled run" in caplog.text


def test_connection_error_is_not_retried(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == WIND:
            raise httpx.ConnectError("no route")
        return httpx.Response(200, content=b"[]")

    caplog.set_level(logging.ERROR)
    with _client(httpx.MockTransport(handler)) as client:
        results = poll_swpc(client, tmp_path, now=WHEN)

    assert results[0].status_code is None
    assert results[0].error == "ConnectError"
    assert results[0].path is None
    assert results[1].status_code == 200
    assert "ConnectError" in caplog.text
    assert "next try is the scheduled run" in caplog.text


def test_scheduler_job_is_every_five_minutes() -> None:
    scheduler = BlockingScheduler(timezone=UTC)
    job = add_swpc_job(scheduler, 5, lambda: None)
    assert job.id == JOB_ID
    assert job.trigger.interval == timedelta(minutes=5)
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time == 60
    assert job.next_run_time is not None


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RAW_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INGEST_USER_AGENT", "TachoclineIndustries/0.1 (test)")
    monkeypatch.setenv("SWPC_POLL_MINUTES", "5")
    settings = SwpcSettings.from_env()
    assert settings.raw_dir == tmp_path
    assert settings.poll_minutes == 5
    assert settings.user_agent.startswith("TachoclineIndustries/")


def test_settings_reject_bad_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAW_DATA_DIR", "/data/raw")
    monkeypatch.setenv("INGEST_USER_AGENT", "ok")
    monkeypatch.setenv("SWPC_POLL_MINUTES", "0")
    with pytest.raises(SwpcConfigError):
        SwpcSettings.from_env()

    monkeypatch.setenv("SWPC_POLL_MINUTES", "five")
    with pytest.raises(SwpcConfigError):
        SwpcSettings.from_env()

    monkeypatch.setenv("SWPC_POLL_MINUTES", "5")
    monkeypatch.setenv("INGEST_USER_AGENT", "bad\nagent")
    with pytest.raises(SwpcConfigError):
        SwpcSettings.from_env()

    monkeypatch.delenv("INGEST_USER_AGENT")
    with pytest.raises(SwpcConfigError):
        SwpcSettings.from_env()
