"""Land CelesTrak SATCAT rows for the starter set, including DECAY_DATE.

Issue #49. Drag Watch needs a decay date to compare with a prediction.
None of the five tracked objects had a decay date on the 2026-10-25
check. The column is still saved, unchanged, so a later date is in the
raw zone when CelesTrak publishes one.

https://celestrak.org/satcat/satcat-format.php

One GET per catalog number, once a day. That is slower than the GP
poll on purpose: a decay date does not move every two hours, and
CelesTrak asks clients not to hammer a group. A 4xx is logged and not
retried. HTTP 429 skips the catalog numbers still left in this run.
This job does not open Postgres. The bytes and the manifest are the
record.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ti_ingest.celestrak_gp import CATALOG_NUMBERS
from ti_ingest.swpc import FetchResult, write_raw

logger = logging.getLogger(__name__)

SOURCE_DIR = "satcat"
POLL_MINUTES = 24 * 60
_URL = "https://celestrak.org/satcat/records.php?CATNR={catnr}&FORMAT=json"


def product_name(catnr: int) -> str:
    """``satcat-`` so these files are not parsed as GP rows."""
    return f"satcat-{catnr}"


def record_url(catnr: int) -> str:
    return _URL.format(catnr=catnr)


def startup_line(raw_dir: str) -> str:
    """One line for the container log. The cadence is one day."""
    ids = ", ".join(str(catnr) for catnr in CATALOG_NUMBERS)
    return (
        f"CelesTrak SATCAT poller scheduled every {POLL_MINUTES} min for "
        f"catalog numbers {ids}. "
        f"raw_dir={raw_dir}/{SOURCE_DIR}. "
        "Each file is saved with a sha256 manifest. Nothing is upserted."
    )


def fetch_record(
    client: httpx.Client,
    raw_dir: Path,
    catnr: int,
    when: datetime,
) -> FetchResult:
    """GET one catalog record once. Do not call this in a retry loop."""
    name = product_name(catnr)
    url = record_url(catnr)
    try:
        response = client.get(url)
    except httpx.TransportError as exc:
        logger.error(
            "SATCAT request failed for %s (%s); next try is the scheduled run",
            name,
            type(exc).__name__,
        )
        return FetchResult(name, None, None, type(exc).__name__, False)

    status = response.status_code
    if 400 <= status < 500:
        stop_run = status == 429
        logger.error("SATCAT returned HTTP %s for %s; not retrying", status, name)
        return FetchResult(name, status, None, f"HTTP {status}", stop_run)
    if status < 200 or status >= 300:
        logger.error(
            "SATCAT returned HTTP %s for %s; next try is the scheduled run",
            status,
            name,
        )
        return FetchResult(name, status, None, f"HTTP {status}", False)

    try:
        path = write_raw(
            raw_dir,
            when,
            name,
            response.content,
            source_dir=SOURCE_DIR,
            url=url,
        )
    except OSError as exc:
        logger.error("Could not write raw %s: %s", name, exc)
        return FetchResult(name, status, None, str(exc), False)

    logger.info("Landed %s (%s bytes) at %s", name, len(response.content), path)
    return FetchResult(name, status, path, None, False)


def poll_satcat(
    client: httpx.Client,
    raw_dir: Path,
    *,
    now: datetime | None = None,
) -> list[FetchResult]:
    """Fetch the five SATCAT records once. Does not open Postgres."""
    moment = now if now is not None else datetime.now(UTC)
    logger.info(
        "Fetching %s SATCAT records into %s",
        len(CATALOG_NUMBERS),
        raw_dir / SOURCE_DIR,
    )
    results: list[FetchResult] = []
    for catnr in CATALOG_NUMBERS:
        result = fetch_record(client, raw_dir, catnr, moment)
        results.append(result)
        if result.stop_run:
            logger.error(
                "Stopping this SATCAT run after %s (HTTP %s); "
                "skipping the other catalog numbers",
                result.product,
                result.status_code,
            )
            break
    return results
