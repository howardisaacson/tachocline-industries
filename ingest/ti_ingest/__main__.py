"""Long-running ingest process: solar wind and GOES X-ray.

Solar wind is issues #26 and #27. GOES X-ray flux is issue #31. Both
are interval jobs on one scheduler, in this one process (ADR 0008).

APScheduler's ``BlockingScheduler`` is the process. ``start()`` does not
return until the scheduler shuts down. Docker stops the container with
SIGTERM; that signal asks the scheduler to stop. An in-flight GET is
not cancelled and is not retried. The next container start fetches again.

Each run lands the raw JSON, validates it, upserts Postgres, and writes
``ingest_log``. Fetch and load stay separate from the scheduler so a
later orchestrator can call the same functions (ADR 0004).

Interval jobs: https://apscheduler.readthedocs.io/en/3.x/userguide.html
"""

from __future__ import annotations

import logging
import signal
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from apscheduler.job import Job
from apscheduler.schedulers.blocking import BlockingScheduler

from ti_ingest.db import connect
from ti_ingest.goes_xray import poll_goes_xray, startup_line
from ti_ingest.load import DBConnection, store_fetch
from ti_ingest.migrate import DatabaseSettings
from ti_ingest.swpc import SwpcSettings, make_client, poll_swpc

logger = logging.getLogger("ti_ingest")

JOB_ID = "swpc_rtsw"
GOES_JOB_ID = "goes_xray"
# A start that is a few seconds late still runs once. Later than this,
# the run is skipped instead of firing a backlog. coalesce does the same
# if several intervals were missed while the process was down.
MISFIRE_GRACE_SECONDS = 60


def startup_message(raw_dir: str, poll_minutes: int) -> str:
    """One line for the container log: what this process will do."""
    return (
        f"SWPC poller scheduled every {poll_minutes} min for "
        f"rtsw_wind_1m and rtsw_mag_1m. "
        f"raw_dir={raw_dir}/swpc_rtsw. "
        "Each file is validated and upserted on (time_tag, source)."
    )


def add_swpc_job(
    scheduler: BlockingScheduler,
    poll_minutes: int,
    job: Callable[[], None],
) -> Job:
    """Register the interval job. Does not start the scheduler.

    ``next_run_time`` is now, so the first fetch happens at startup
    instead of after a quiet five minutes. ``max_instances=1`` means a
    slow fetch does not overlap the next one. ``coalesce`` collapses a
    missed backlog into a single run.
    """
    if poll_minutes < 1:
        raise ValueError("poll_minutes must be at least 1")
    return scheduler.add_job(
        job,
        "interval",
        minutes=poll_minutes,
        id=JOB_ID,
        name="SWPC rtsw_wind_1m and rtsw_mag_1m",
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )


def add_goes_job(
    scheduler: BlockingScheduler,
    poll_minutes: int,
    job: Callable[[], None],
) -> Job:
    """Register the X-ray interval. Same cadence as solar wind.

    There is no second environment variable. Both jobs read
    ``SWPC_POLL_MINUTES``. A different cadence later would be a new
    variable, not a change to this default.
    """
    if poll_minutes < 1:
        raise ValueError("poll_minutes must be at least 1")
    return scheduler.add_job(
        job,
        "interval",
        minutes=poll_minutes,
        id=GOES_JOB_ID,
        name="GOES primary xrays-6-hour",
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )


def build_scheduler(
    poll_minutes: int,
    swpc_job: Callable[[], None],
    goes_job: Callable[[], None],
) -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=UTC)
    add_swpc_job(scheduler, poll_minutes, swpc_job)
    add_goes_job(scheduler, poll_minutes, goes_job)
    return scheduler


def execute_swpc_job(
    settings: SwpcSettings,
    database: DatabaseSettings,
    *,
    transport: httpx.BaseTransport | None = None,
    connect_fn: Callable[[DatabaseSettings], DBConnection] = connect,
    now: datetime | None = None,
) -> None:
    """One scheduled run. Land raw files first, then open Postgres.

    If the database is down, the raw files stay on disk and this function
    returns. It does not raise: the scheduler waits for the next interval
    instead of retrying immediately. ``transport`` and ``connect_fn`` are
    how tests substitute the network and the database.
    """
    started = now if now is not None else datetime.now(UTC)
    with make_client(settings.user_agent, transport=transport) as client:
        fetches = poll_swpc(client, settings.raw_dir, now=started)
    try:
        conn = connect_fn(database)
    except Exception:
        logger.exception(
            "Postgres is unavailable; raw SWPC files were kept and not upserted"
        )
        return
    try:
        for fetch in fetches:
            try:
                store_fetch(conn, fetch, started_at=started)
            except Exception:
                logger.exception("SWPC store failed for %s", fetch.product)
    finally:
        conn.close()


def execute_goes_job(
    settings: SwpcSettings,
    database: DatabaseSettings,
    *,
    transport: httpx.BaseTransport | None = None,
    connect_fn: Callable[[DatabaseSettings], DBConnection] = connect,
    now: datetime | None = None,
) -> None:
    """One X-ray run. Land the raw file first, then open Postgres.

    A database outage keeps the raw file and returns. It does not raise,
    so the scheduler waits for the next interval. This job does not fetch
    solar wind, and the solar-wind job does not fetch X-rays. A 429 on
    one feed does not skip the other.
    """
    started = now if now is not None else datetime.now(UTC)
    with make_client(settings.user_agent, transport=transport) as client:
        fetches = poll_goes_xray(client, settings.raw_dir, now=started)
    try:
        conn = connect_fn(database)
    except Exception:
        logger.exception(
            "Postgres is unavailable; raw GOES X-ray file was kept and not upserted"
        )
        return
    try:
        for fetch in fetches:
            try:
                store_fetch(conn, fetch, started_at=started)
            except Exception:
                logger.exception("GOES X-ray store failed for %s", fetch.product)
    finally:
        conn.close()


def make_job(settings: SwpcSettings, database: DatabaseSettings) -> Callable[[], None]:
    """One solar-wind run. The HTTP client closes before the next interval."""

    def job() -> None:
        execute_swpc_job(settings, database)

    return job


def make_goes_job(
    settings: SwpcSettings, database: DatabaseSettings
) -> Callable[[], None]:
    """One X-ray run. The HTTP client closes before the next interval."""

    def job() -> None:
        execute_goes_job(settings, database)

    return job


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = SwpcSettings.from_env()
    database = DatabaseSettings.from_env()
    logger.info("%s", startup_message(str(settings.raw_dir), settings.poll_minutes))
    logger.info("%s", startup_line(str(settings.raw_dir), settings.poll_minutes))
    scheduler = build_scheduler(
        settings.poll_minutes,
        make_job(settings, database),
        make_goes_job(settings, database),
    )

    def handle_stop(signum: int, _frame: object) -> None:
        logger.info("Received signal %s; stopping", signum)
        if scheduler.running:
            # wait=False returns without blocking on the GET. The request
            # is not sent again.
            scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    scheduler.start()
    logger.info("Ingest process stopped")


if __name__ == "__main__":
    main()
