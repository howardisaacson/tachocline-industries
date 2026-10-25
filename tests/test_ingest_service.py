"""The ingest process schedules the SWPC poller (issue #26)."""

from ti_ingest.__main__ import startup_message


def test_startup_message_names_the_poller_and_landing_zone() -> None:
    message = startup_message("/data/raw", 5)
    assert "every 5 min" in message
    assert "rtsw_wind_1m" in message
    assert "rtsw_mag_1m" in message
    assert "/data/raw/swpc_rtsw" in message
    assert "issue #27" in message
