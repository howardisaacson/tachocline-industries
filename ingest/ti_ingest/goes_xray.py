"""Fetch NOAA SWPC GOES X-ray flux into the raw landing zone.

This is the second poller (issue #31). It follows the same steps as
``ti_ingest.swpc`` (ADR 0004): one GET, save the body unchanged, and
leave parsing to ``ti_ingest.load``. The file is the primary satellite's
last six hours of 1-minute flux, two energy bands per minute.

``xrays-6-hour.json`` is the URL ``docs/research/data_sources.md`` already
verified. The 1-day and 7-day files are the same product with a longer
window. They are not polled here. A laptop that is off for longer than
six hours cannot backfill that gap from this file.

One run makes one GET. A 4xx response is logged and not retried. The
next attempt is the next scheduled run. The client, timeout, and
``User-Agent`` are the same objects the solar-wind poller uses.

httpx timeouts: https://www.python-httpx.org/advanced/timeouts/
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ti_ingest.swpc import FetchResult, write_raw

logger = logging.getLogger(__name__)

# ADR 0004 layout: data/raw/<source>/<YYYY-MM-DD>/<timestamp>_<product>.json
SOURCE_DIR = "goes_xray"
PRODUCT_NAME = "xrays-6-hour"
PRODUCT_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json"


def startup_line(raw_dir: str, poll_minutes: int) -> str:
    """One line for the container log, beside the solar-wind line."""
    return (
        f"GOES X-ray poller scheduled every {poll_minutes} min for "
        f"{PRODUCT_NAME}. "
        f"raw_dir={raw_dir}/{SOURCE_DIR}. "
        "Rows are validated and upserted on (time_tag, satellite, energy)."
    )


def fetch_xrays(
    client: httpx.Client,
    raw_dir: Path,
    when: datetime,
) -> FetchResult:
    """GET the 6-hour file once. Do not call this in a retry loop."""
    try:
        response = client.get(PRODUCT_URL)
    except httpx.TransportError as exc:
        logger.error(
            "GOES X-ray request failed (%s); next try is the scheduled run",
            type(exc).__name__,
        )
        return FetchResult(PRODUCT_NAME, None, None, type(exc).__name__, False)

    status = response.status_code
    if 400 <= status < 500:
        # 429 Too Many Requests: nothing else is fetched in this job.
        stop_run = status == 429
        logger.error(
            "GOES X-ray returned HTTP %s for %s; not retrying",
            status,
            PRODUCT_NAME,
        )
        return FetchResult(PRODUCT_NAME, status, None, f"HTTP {status}", stop_run)
    if status < 200 or status >= 300:
        logger.error(
            "GOES X-ray returned HTTP %s for %s; next try is the scheduled run",
            status,
            PRODUCT_NAME,
        )
        return FetchResult(PRODUCT_NAME, status, None, f"HTTP {status}", False)

    try:
        path = write_raw(
            raw_dir,
            when,
            PRODUCT_NAME,
            response.content,
            source_dir=SOURCE_DIR,
        )
    except OSError as exc:
        logger.error("Could not write raw %s: %s", PRODUCT_NAME, exc)
        return FetchResult(PRODUCT_NAME, status, None, str(exc), False)

    logger.info(
        "Landed %s (%s bytes) at %s",
        PRODUCT_NAME,
        len(response.content),
        path,
    )
    return FetchResult(PRODUCT_NAME, status, path, None, False)


def poll_goes_xray(
    client: httpx.Client,
    raw_dir: Path,
    *,
    now: datetime | None = None,
) -> list[FetchResult]:
    """Fetch the X-ray file once. Does not parse JSON or open Postgres.

    The list has one item so the job runner can store each attempted
    file the same way it stores solar wind. There is no second file in
    this job: integral protons are a different product and are not fetched.
    """
    moment = now if now is not None else datetime.now(UTC)
    logger.info("Fetching GOES X-ray flux into %s", raw_dir / SOURCE_DIR)
    return [fetch_xrays(client, raw_dir, moment)]
