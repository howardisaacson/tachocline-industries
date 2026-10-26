"""Fetch NOAA SWPC Kp and alerts into the raw landing zone.

This is the third poller (issue #32). It follows ``ti_ingest.swpc``
(ADR 0004): one GET per file, save the body unchanged, and leave parsing
to ``ti_ingest.load``. Three files, all named in
``docs/research/data_sources.md`` and still served on 2026-10-25:

* ``planetary_k_index_1m.json``, 1-minute estimated Kp
* ``noaa-planetary-k-index.json``, estimated 3-hour Kp
* ``alerts.json``, alert, watch, and warning text

The aurora grid and the solar-cycle file in that same note are not
fetched. One run makes one GET per file. A 4xx response is logged and
not retried. HTTP 429 skips the files still left in this run. The next
attempt is the next scheduled run. The client, timeout, and
``User-Agent`` are the same objects the solar-wind poller uses.

httpx timeouts: https://www.python-httpx.org/advanced/timeouts/
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ti_ingest.swpc import FetchResult, SwpcProduct, write_raw

logger = logging.getLogger(__name__)

# ADR 0004 layout: data/raw/<source>/<YYYY-MM-DD>/<timestamp>_<product>.json
SOURCE_DIR = "swpc_kp"

PRODUCTS: tuple[SwpcProduct, ...] = (
    SwpcProduct(
        "planetary_k_index_1m",
        "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
    ),
    SwpcProduct(
        "noaa-planetary-k-index",
        "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    ),
    SwpcProduct(
        "alerts",
        "https://services.swpc.noaa.gov/products/alerts.json",
    ),
)


def startup_line(raw_dir: str, poll_minutes: int) -> str:
    """One line for the container log, beside the solar-wind line."""
    names = ", ".join(product.name for product in PRODUCTS)
    return (
        f"Kp and alerts poller scheduled every {poll_minutes} min for "
        f"{names}. "
        f"raw_dir={raw_dir}/{SOURCE_DIR}. "
        "Kp rows upsert on time_tag. Alerts upsert on "
        "(issue_datetime, product_id)."
    )


def fetch_product(
    client: httpx.Client,
    raw_dir: Path,
    product: SwpcProduct,
    when: datetime,
) -> FetchResult:
    """GET one file once. Do not call this in a retry loop."""
    try:
        response = client.get(product.url)
    except httpx.TransportError as exc:
        logger.error(
            "Kp/alerts request failed for %s (%s); next try is the scheduled run",
            product.name,
            type(exc).__name__,
        )
        return FetchResult(product.name, None, None, type(exc).__name__, False)

    status = response.status_code
    if 400 <= status < 500:
        # 429 Too Many Requests: do not ask for the other files this run.
        stop_run = status == 429
        logger.error(
            "Kp/alerts returned HTTP %s for %s; not retrying",
            status,
            product.name,
        )
        return FetchResult(product.name, status, None, f"HTTP {status}", stop_run)
    if status < 200 or status >= 300:
        logger.error(
            "Kp/alerts returned HTTP %s for %s; next try is the scheduled run",
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


def poll_kp_alerts(
    client: httpx.Client,
    raw_dir: Path,
    *,
    now: datetime | None = None,
) -> list[FetchResult]:
    """Fetch the three files once. Same timestamp so the landing names pair.

    Does not parse the JSON and does not open a database connection.
    """
    moment = now if now is not None else datetime.now(UTC)
    logger.info(
        "Fetching %s Kp/alerts files into %s",
        len(PRODUCTS),
        raw_dir / SOURCE_DIR,
    )
    results: list[FetchResult] = []
    for product in PRODUCTS:
        result = fetch_product(client, raw_dir, product, moment)
        results.append(result)
        if result.stop_run:
            logger.error(
                "Stopping this Kp/alerts run after %s (HTTP %s); "
                "skipping the other files",
                product.name,
                result.status_code,
            )
            break
    return results
