"""Fetch the GFZ definitive Kp file and turn each day into eight rows.

The file is one line per UT day, with Kp1..Kp8 and ap1..ap8. This module
does not store the sunspot column. That series is CC BY-NC. Kp and ap in
the same file are CC BY 4.0.

https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt
https://doi.org/10.5880/Kp.0001

The job runs once a day, not on ``SWPC_POLL_MINUTES``. The file is a few
megabytes and the recent rows are nowcasts that later become definitive,
so the upsert replaces them. A 4xx is logged and not retried.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from ti_ingest.models import GfzKpRow
from ti_ingest.swpc import FetchResult, SwpcProduct, write_raw

logger = logging.getLogger(__name__)

SOURCE_DIR = "gfz_kp"
PRODUCT_NAME = "gfz-kp-3h"
# Once a day. The file is republished when nowcasts are replaced.
POLL_MINUTES = 24 * 60
FILE_URL = "https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt"

# Header, checked 2026-10-27: eight Kp values, then eight ap values, then
# Ap, sunspot number, two F10.7 columns, and the definitive flag.
_KP_START = 7
_AP_START = 15
_FLAG_INDEX = 27
_FIELD_COUNT = 28
_HOURS = (0, 3, 6, 9, 12, 15, 18, 21)

PRODUCT = SwpcProduct(PRODUCT_NAME, FILE_URL)


def startup_line(raw_dir: str) -> str:
    """One line for the container log. The cadence is one day."""
    return (
        f"GFZ Kp poller scheduled every {POLL_MINUTES} min. "
        f"raw_dir={raw_dir}/{SOURCE_DIR}. "
        "Rows upsert on time_tag. Sunspot numbers are not stored."
    )


def parse_gfz_text(body: bytes) -> tuple[list[GfzKpRow], int, str | None]:
    """Return rows, a reject count, and a file-level error.

    A data line that is the wrong width, or whose Kp is outside 0 to 9,
    counts as one reject. A Kp of -1 is a published gap and is skipped,
    not rejected. Comment lines are not rows.
    """
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [], 0, f"UnicodeDecodeError: {exc}"

    rows: list[GfzKpRow] = []
    rejected = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != _FIELD_COUNT:
            rejected += 1
            continue
        try:
            day = datetime(
                int(fields[0]),
                int(fields[1]),
                int(fields[2]),
                tzinfo=UTC,
            )
            flag = int(fields[_FLAG_INDEX])
        except ValueError:
            rejected += 1
            continue
        if flag not in (0, 1, 2):
            rejected += 1
            continue
        line_ok = True
        built: list[GfzKpRow] = []
        for index, hour in enumerate(_HOURS):
            try:
                kp = float(fields[_KP_START + index])
                ap = int(fields[_AP_START + index])
            except ValueError:
                line_ok = False
                break
            if kp == -1.0:
                continue
            if kp < 0 or kp > 9:
                line_ok = False
                break
            built.append(
                GfzKpRow(
                    time_tag=day.replace(hour=hour),
                    kp=kp,
                    ap=None if ap < 0 else ap,
                    definitive=flag >= 1,
                )
            )
        if not line_ok:
            rejected += 1
            continue
        rows.extend(built)
    return rows, rejected, None


def fetch_gfz(
    client: httpx.Client,
    raw_dir,
    when: datetime,
) -> FetchResult:
    """GET the file once. Do not call this in a retry loop."""
    try:
        response = client.get(PRODUCT.url)
    except httpx.TransportError as exc:
        logger.error(
            "GFZ request failed (%s); next try is the scheduled run",
            type(exc).__name__,
        )
        return FetchResult(PRODUCT.name, None, None, type(exc).__name__, False)

    status = response.status_code
    if status < 200 or status >= 300:
        logger.error("GFZ returned HTTP %s; not retrying", status)
        return FetchResult(PRODUCT.name, status, None, f"HTTP {status}", status == 429)

    try:
        path = write_raw(
            raw_dir,
            when,
            PRODUCT.name,
            response.content,
            source_dir=SOURCE_DIR,
            suffix=".txt",
        )
    except OSError as exc:
        logger.error("Could not write raw %s: %s", PRODUCT.name, exc)
        return FetchResult(PRODUCT.name, status, None, str(exc), False)

    logger.info("Landed %s (%s bytes) at %s", PRODUCT.name, len(response.content), path)
    return FetchResult(PRODUCT.name, status, path, None, False)
