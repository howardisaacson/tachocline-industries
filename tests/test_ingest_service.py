"""The ingest process is a placeholder until issue #26."""

from ti_ingest.__main__ import startup_message


def test_startup_message_says_there_is_no_poller() -> None:
    message = startup_message("/data/raw")
    assert "issue #26" in message
    assert "/data/raw" in message
    assert "http" not in message.lower()
