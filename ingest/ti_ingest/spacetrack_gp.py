"""Backfill GP history from Space-Track when an account is configured.

The current CelesTrak poll stores one epoch every two hours. Decay needs
the epochs before that. Space-Track's ``gp_history`` class is the same
mean elements, behind a free account. The query shape is the one in
their public documentation: ``/basicspacedata/query/class/...``.

https://www.space-track.org/documentation
https://www.space-track.org/basicspacedata/modeldef/class/gp_history/format/html

Login is one POST. The password stays in the request body. It is not
logged and it is not put on the URL. Empty credentials skip the job.
A 401 or 429 stops the rest of that run. The window is the last 400
days, once a day, not the two-hour CelesTrak cadence.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from ti_ingest.celestrak_gp import CATALOG_NUMBERS
from ti_ingest.swpc import FetchResult, write_raw

logger = logging.getLogger(__name__)

SOURCE_DIR = "spacetrack_gp"
POLL_MINUTES = 24 * 60
HISTORY_DAYS = 400
LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
_QUERY = (
    "https://www.space-track.org/basicspacedata/query/class/gp_history"
    "/NORAD_CAT_ID/{catnr}/EPOCH/%3Enow-"
    + str(HISTORY_DAYS)
    + "/orderby/EPOCH%20asc/format/json"
)


def product_name(catnr: int) -> str:
    """``gp-hist-`` so the 5-minute health stat keeps skipping orbit files."""
    return f"gp-hist-{catnr}"


@dataclass(frozen=True)
class SpaceTrackSettings:
    """Account for ``gp_history``. ``enabled`` is false when either value is empty."""

    user: str
    password: str
    enabled: bool

    @classmethod
    def from_env(cls) -> SpaceTrackSettings:
        user = os.environ.get("SPACETRACK_USER", "").strip()
        password = os.environ.get("SPACETRACK_PASSWORD", "").strip()
        if "\n" in user or "\r" in user or "\n" in password or "\r" in password:
            raise ValueError("SPACETRACK_USER and SPACETRACK_PASSWORD must be one line")
        return cls(user=user, password=password, enabled=bool(user and password))


def startup_line(raw_dir: str, enabled: bool) -> str:
    """One line for the container log. The password is not included."""
    if not enabled:
        return (
            "Space-Track gp_history skipped: SPACETRACK_USER or "
            "SPACETRACK_PASSWORD is empty."
        )
    ids = ", ".join(str(catnr) for catnr in CATALOG_NUMBERS)
    return (
        f"Space-Track gp_history scheduled every {POLL_MINUTES} min "
        f"for the last {HISTORY_DAYS} days, catalog numbers {ids}. "
        f"raw_dir={raw_dir}/{SOURCE_DIR}."
    )


def history_url(catnr: int) -> str:
    return _QUERY.format(catnr=catnr)


def poll_spacetrack(
    client: httpx.Client,
    raw_dir: Path,
    settings: SpaceTrackSettings,
    when: datetime,
) -> list[FetchResult]:
    """Log in once, then one GET per catalog number. No retry loop."""
    if not settings.enabled:
        logger.info("%s", startup_line(str(raw_dir), False))
        return []

    try:
        login = client.post(
            LOGIN_URL,
            data={"identity": settings.user, "password": settings.password},
        )
    except httpx.TransportError as exc:
        logger.error("Space-Track login failed (%s)", type(exc).__name__)
        return [FetchResult("gp-hist-login", None, None, type(exc).__name__, True)]

    if login.status_code < 200 or login.status_code >= 300:
        logger.error(
            "Space-Track login returned HTTP %s; not retrying", login.status_code
        )
        return [
            FetchResult(
                "gp-hist-login",
                login.status_code,
                None,
                f"HTTP {login.status_code}",
                True,
            )
        ]

    results: list[FetchResult] = []
    for catnr in CATALOG_NUMBERS:
        name = product_name(catnr)
        try:
            response = client.get(history_url(catnr))
        except httpx.TransportError as exc:
            logger.error(
                "Space-Track request failed for %s (%s)", name, type(exc).__name__
            )
            results.append(FetchResult(name, None, None, type(exc).__name__, False))
            continue
        status = response.status_code
        if status < 200 or status >= 300:
            stop_run = status in (401, 429)
            logger.error(
                "Space-Track returned HTTP %s for %s; not retrying", status, name
            )
            results.append(FetchResult(name, status, None, f"HTTP {status}", stop_run))
            if stop_run:
                break
            continue
        try:
            path = write_raw(
                raw_dir,
                when,
                name,
                response.content,
                source_dir=SOURCE_DIR,
            )
        except OSError as exc:
            logger.error("Could not write raw %s: %s", name, exc)
            results.append(FetchResult(name, status, None, str(exc), False))
            continue
        logger.info("Landed %s (%s bytes) at %s", name, len(response.content), path)
        results.append(FetchResult(name, status, path, None, False))
    return results
