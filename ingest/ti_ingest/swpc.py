"""Fetch NOAA SWPC real-time solar wind into the raw landing zone.

A poller asks for a URL on a schedule. This one asks for two files
(ADR 0003): plasma (``rtsw_wind_1m``) and magnetic field
(``rtsw_mag_1m``). Each response is saved exactly as received, before
any parsing. That folder is the raw landing zone (ADR 0004): bronze in
the medallion pattern. ``ti_ingest.load`` validates the JSON and upserts it.

One run makes one GET per file. A 4xx response is logged and not
retried: repeating a "not found" or "slow down" does not help, and it
can get a client blocked. The next attempt is the next scheduled run.

httpx timeouts: https://www.python-httpx.org/advanced/timeouts/
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Folder name from issue #26. The date under it is YYYY-MM-DD in UTC,
# which is the layout ADR 0004 names ``<source>/<YYYY-MM-DD>/``.
SOURCE_DIR = "swpc_rtsw"

# The files are about 2 MB (docs/research/data_sources.md). Connect fails
# fast. Read allows a slow link. This is one attempt, not a retry loop.
HTTP_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

SWPC_RTSW_BASE = "https://services.swpc.noaa.gov/json/rtsw"


class SwpcConfigError(Exception):
    """A required poller setting is missing or not usable."""


@dataclass(frozen=True)
class SwpcProduct:
    """One SWPC JSON file.

    ``name`` is the file (``rtsw_wind_1m``), not the spacecraft id inside
    it. Several spacecraft share one file. ``ti_ingest.load`` splits the rows.
    """

    name: str
    url: str


PRODUCTS: tuple[SwpcProduct, ...] = (
    SwpcProduct("rtsw_wind_1m", f"{SWPC_RTSW_BASE}/rtsw_wind_1m.json"),
    SwpcProduct("rtsw_mag_1m", f"{SWPC_RTSW_BASE}/rtsw_mag_1m.json"),
)


@dataclass(frozen=True)
class SwpcSettings:
    """What the poller reads from the environment. No database settings."""

    raw_dir: Path
    user_agent: str
    poll_minutes: int

    @classmethod
    def from_env(cls) -> SwpcSettings:
        missing: list[str] = []
        values: dict[str, str] = {}
        for name in ("RAW_DATA_DIR", "INGEST_USER_AGENT", "SWPC_POLL_MINUTES"):
            value = os.environ.get(name, "").strip()
            if not value:
                missing.append(name)
            else:
                values[name] = value
        if missing:
            raise SwpcConfigError(
                f"Missing environment variables: {', '.join(missing)}"
            )
        user_agent = values["INGEST_USER_AGENT"]
        if "\n" in user_agent or "\r" in user_agent:
            raise SwpcConfigError("INGEST_USER_AGENT must be a single line")
        try:
            poll_minutes = int(values["SWPC_POLL_MINUTES"])
        except ValueError as exc:
            raise SwpcConfigError("SWPC_POLL_MINUTES must be an integer") from exc
        if poll_minutes < 1:
            raise SwpcConfigError("SWPC_POLL_MINUTES must be at least 1")
        return cls(
            raw_dir=Path(values["RAW_DATA_DIR"]),
            user_agent=user_agent,
            poll_minutes=poll_minutes,
        )


@dataclass(frozen=True)
class FetchResult:
    """What one GET did. ``path`` is set only when the body was saved."""

    product: str
    status_code: int | None
    path: Path | None
    error: str | None
    stop_run: bool


def make_client(
    user_agent: str,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """HTTP client for one poll run.

    ``User-Agent`` names this project so an operator at SWPC can see who
    is calling. ``transport`` is for tests; production leaves it unset
    and httpx uses the network.
    """
    return httpx.Client(
        transport=transport,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        follow_redirects=True,
    )


def landing_path(raw_dir: Path, when: datetime, product: str) -> Path:
    """``<raw_dir>/swpc_rtsw/<YYYY-MM-DD>/<timestamp>_<product>.json``.

    The clock is UTC so the folder date and the filename agree. Wind and
    mag share the directory from issue #26; the product name is in the
    file so the second write does not replace the first.
    """
    if when.tzinfo is None:
        raise ValueError("landing timestamps must be timezone-aware")
    utc = when.astimezone(UTC)
    directory = raw_dir / SOURCE_DIR / utc.strftime("%Y-%m-%d")
    filename = f"{utc.strftime('%Y%m%dT%H%M%SZ')}_{product}.json"
    return directory / filename


def write_raw(raw_dir: Path, when: datetime, product: str, body: bytes) -> Path:
    """Save ``body`` unchanged. A crash mid-write leaves a ``.partial`` file."""
    path = landing_path(raw_dir, when, product)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_bytes(body)
    partial.replace(path)
    return path


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
            "SWPC request failed for %s (%s); next try is the scheduled run",
            product.name,
            type(exc).__name__,
        )
        return FetchResult(product.name, None, None, type(exc).__name__, False)

    status = response.status_code
    if 400 <= status < 500:
        # 429 Too Many Requests: do not ask for the other file this run.
        stop_run = status == 429
        logger.error(
            "SWPC returned HTTP %s for %s; not retrying",
            status,
            product.name,
        )
        return FetchResult(product.name, status, None, f"HTTP {status}", stop_run)
    if status < 200 or status >= 300:
        logger.error(
            "SWPC returned HTTP %s for %s; next try is the scheduled run",
            status,
            product.name,
        )
        return FetchResult(product.name, status, None, f"HTTP {status}", False)

    try:
        path = write_raw(raw_dir, when, product.name, response.content)
    except OSError as exc:
        logger.error("Could not write raw %s: %s", product.name, exc)
        return FetchResult(product.name, status, None, str(exc), False)

    logger.info("Landed %s (%s bytes) at %s", product.name, len(response.content), path)
    return FetchResult(product.name, status, path, None, False)


def poll_swpc(
    client: httpx.Client,
    raw_dir: Path,
    *,
    now: datetime | None = None,
) -> list[FetchResult]:
    """Fetch both products once. Same timestamp so the two files pair up.

    Does not parse the JSON and does not open a database connection.
    """
    moment = now if now is not None else datetime.now(UTC)
    logger.info("Fetching %s SWPC files into %s", len(PRODUCTS), raw_dir / SOURCE_DIR)
    results: list[FetchResult] = []
    for product in PRODUCTS:
        result = fetch_product(client, raw_dir, product, moment)
        results.append(result)
        if result.stop_run:
            logger.error(
                "Stopping this SWPC run after %s (HTTP %s); skipping the other files",
                product.name,
                result.status_code,
            )
            break
    return results
