"""Fetch CelesTrak GP records for the starter satellite set.

Issue #34. The five catalog numbers are the set in
``docs/research/tracked-satellites.md``. Each URL is the single-catalog
form CelesTrak documents: ``CATNR`` returns one object, and ``FORMAT=json``
is required because the default format became CSV in May 2026.

https://celestrak.org/NORAD/documentation/gp-data-formats.php

CelesTrak checks for new GP data once every two hours, so this job does
too. It does not read ``SWPC_POLL_MINUTES``. A 4xx is logged and not
retried. HTTP 429 skips the catalog numbers still left in this run.
Space-Track ``gp_history`` is not fetched. That backfill needs an account
and is optional for this issue.

One run makes one GET per catalog number. The body is saved unchanged.
``ti_ingest.load`` validates it and derives altitude.

httpx timeouts: https://www.python-httpx.org/advanced/timeouts/
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ti_ingest.swpc import FetchResult, SwpcProduct, write_raw

logger = logging.getLogger(__name__)

SOURCE_DIR = "celestrak_gp"
# CelesTrak's own update cadence. Do not lower this.
POLL_MINUTES = 120

# Order matches docs/research/tracked-satellites.md.
CATALOG_NUMBERS: tuple[int, ...] = (25544, 39084, 49260, 20580, 28485)

_GP_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR={catnr}&FORMAT=json"


def _product(catnr: int) -> SwpcProduct:
    return SwpcProduct(f"gp-{catnr}", _GP_URL.format(catnr=catnr))


PRODUCTS: tuple[SwpcProduct, ...] = tuple(_product(catnr) for catnr in CATALOG_NUMBERS)


def startup_line(raw_dir: str) -> str:
    """One line for the container log. The cadence is fixed at two hours."""
    ids = ", ".join(str(catnr) for catnr in CATALOG_NUMBERS)
    return (
        f"CelesTrak GP poller scheduled every {POLL_MINUTES} min for "
        f"catalog numbers {ids}. "
        f"raw_dir={raw_dir}/{SOURCE_DIR}. "
        "Rows upsert on (epoch, norad_cat_id). "
        "Altitude is derived from mean motion and eccentricity."
    )


def fetch_product(
    client: httpx.Client,
    raw_dir: Path,
    product: SwpcProduct,
    when: datetime,
) -> FetchResult:
    """GET one catalog number once. Do not call this in a retry loop."""
    try:
        response = client.get(product.url)
    except httpx.TransportError as exc:
        logger.error(
            "CelesTrak request failed for %s (%s); next try is the scheduled run",
            product.name,
            type(exc).__name__,
        )
        return FetchResult(product.name, None, None, type(exc).__name__, False)

    status = response.status_code
    if 400 <= status < 500:
        stop_run = status == 429
        logger.error(
            "CelesTrak returned HTTP %s for %s; not retrying",
            status,
            product.name,
        )
        return FetchResult(product.name, status, None, f"HTTP {status}", stop_run)
    if status < 200 or status >= 300:
        logger.error(
            "CelesTrak returned HTTP %s for %s; next try is the scheduled run",
            status,
            product.name,
        )
        return FetchResult(product.name, status, None, f"HTTP {status}", False)

    try:
        path = write_raw(
            raw_dir,
            when,
            product.name,
            response.content,
            source_dir=SOURCE_DIR,
        )
    except OSError as exc:
        logger.error("Could not write raw %s: %s", product.name, exc)
        return FetchResult(product.name, status, None, str(exc), False)

    logger.info(
        "Landed %s (%s bytes) at %s",
        product.name,
        len(response.content),
        path,
    )
    return FetchResult(product.name, status, path, None, False)


def poll_celestrak_gp(
    client: httpx.Client,
    raw_dir: Path,
    *,
    now: datetime | None = None,
) -> list[FetchResult]:
    """Fetch the five GP files once. Does not parse JSON or open Postgres."""
    moment = now if now is not None else datetime.now(UTC)
    logger.info(
        "Fetching %s CelesTrak GP files into %s",
        len(PRODUCTS),
        raw_dir / SOURCE_DIR,
    )
    results: list[FetchResult] = []
    for product in PRODUCTS:
        result = fetch_product(client, raw_dir, product, moment)
        results.append(result)
        if result.stop_run:
            logger.error(
                "Stopping this CelesTrak run after %s (HTTP %s); "
                "skipping the other catalog numbers",
                product.name,
                result.status_code,
            )
            break
    return results
