"""Idle ingest process.

`python -m ti_ingest` stays running so Compose can show the service as up.
Issue #26 adds the SWPC poller. This process does not open a socket.
"""

from __future__ import annotations

import logging
import os
import signal
import time

logger = logging.getLogger("ti_ingest")


def startup_message(raw_dir: str) -> str:
    """One line that states the process is idle on purpose."""
    return (
        "Ingest process started. No pollers are registered yet "
        f"(GitHub issue #26). raw_dir={raw_dir}"
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    raw_dir = os.environ.get("RAW_DATA_DIR", "/data/raw")
    logger.info("%s", startup_message(raw_dir))
    stop = False

    def handle_stop(signum: int, _frame: object) -> None:
        nonlocal stop
        logger.info("Received signal %s; stopping", signum)
        stop = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    while not stop:
        time.sleep(1)
    logger.info("Ingest process stopped")


if __name__ == "__main__":
    main()
