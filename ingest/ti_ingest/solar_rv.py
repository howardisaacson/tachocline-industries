"""Fetch NEID and EXPRES Level 2 solar radial velocities.

Both tables are public on the NExScI TAP service. One daily run asks
for the last 14 days of scalar columns. It does not download FITS files.

Checked 2026-11-05 against TAP_SCHEMA and two sample rows:

- NEID ``ccfrvmod`` and ``dvrms`` are km/s. The row at 2026-11-02
  17:17:50 UTC had ccfrvmod −0.6401 and dvrms 0.0003.
- EXPRES ``ccfrvmod`` is km/s. ``v`` and ``e_v`` are cm/s. The row at
  2024-09-30 15:35:58 UTC had ccfrvmod −0.6406, v −64057.073, and
  e_v 19.692. ``dvrms`` on that row was also 19.692, so it matches
  ``e_v`` even though TAP_SCHEMA labels ``dvrms`` as km/s. This module
  reads ``e_v`` for the EXPRES uncertainty and does not read ``dvrms``.

``obsdate`` is UTC and becomes ``time_tag``. ``ccfjdsum`` is kept beside
it. The NEID help page calls that column BJD. The EXPRES TAP description
calls it JD of the geometric midpoint.

https://neid.ipac.caltech.edu/TAP/sync
https://neid.ipac.caltech.edu/help_solar.php
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from pydantic import ValidationError

from ti_ingest.models import SolarRvRow
from ti_ingest.swpc import FetchResult, write_raw

logger = logging.getLogger(__name__)

SOURCE_DIR = "solar_rv"
POLL_MINUTES = 24 * 60
KEEP_DAYS = 14
# Fourteen days of NEID solar exposures is a few thousand rows.
# 20000 leaves room for both instruments without pulling a spectrum.
MAX_REC = 20000
TAP_SYNC_URL = "https://neid.ipac.caltech.edu/TAP/sync"
# Unix epoch 1970-01-01 00:00 UTC is Julian date 2440587.5.
_UNIX_EPOCH_JD = 2440587.5
_KM_TO_M = 1000.0
_CM_TO_M = 0.01
_MISSING = {"", "none", "null", "nan"}


@dataclass(frozen=True)
class _Instrument:
    """One TAP table and the unit of its uncertainty column."""

    product: str
    table: str
    columns: str
    instrument: str
    time_scale: str
    error_in: str


INSTRUMENTS: tuple[_Instrument, ...] = (
    _Instrument(
        product="solar-rv-neid",
        table="neidsolarl2",
        columns="obsdate, ccfrvmod, dvrms, extsnr, exptime, ccfjdsum",
        instrument="neid",
        time_scale="BJD",
        error_in="km/s",
    ),
    _Instrument(
        product="solar-rv-expres",
        table="expressolarl2",
        columns="obsdate, ccfrvmod, e_v, extsnr, exptime, ccfjdsum",
        instrument="expres",
        time_scale="JD",
        error_in="cm/s",
    ),
)
SOLAR_PRODUCTS = {item.product: item for item in INSTRUMENTS}


def startup_line(raw_dir: str) -> str:
    """One line for the container log. The cadence is one day."""
    return (
        f"Solar RV poller scheduled every {POLL_MINUTES} min. "
        f"raw_dir={raw_dir}/{SOURCE_DIR}. "
        "NEID and EXPRES Level 2 scalars only. FITS files are not downloaded."
    )


def julian_day(moment: datetime) -> float:
    """Julian date of an absolute instant. Used only to filter ``obsjd``."""
    utc = moment.astimezone(UTC)
    return utc.timestamp() / 86400.0 + _UNIX_EPOCH_JD


def parse_solar_csv(
    body: bytes, product: str
) -> tuple[list[SolarRvRow], int, str | None]:
    """Return rows, a reject count, and a file-level error.

    A data row with a bad clock counts as one reject. An empty
    ``ccfrvmod`` is a stored gap, not a reject. ``dvrms`` of 9999, and
    any uncertainty outside 0 to 100 m/s after conversion, is stored as
    a null error. A velocity outside ±5000 m/s is stored as a null
    velocity. On 2026-11-05 those two sentinels were the same failed
    exposures: 69 of 2182 NEID rows, 19 of them with velocities from
    about 9 to 97 km/s.
    """
    spec = SOLAR_PRODUCTS.get(product)
    if spec is None:
        return [], 0, f"unknown solar product {product}"
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [], 0, f"UnicodeDecodeError: {exc}"
    stripped = text.lstrip()
    if not stripped:
        return [], 0, "TAP body is empty"
    if stripped.startswith(("<", "Failed")):
        return [], 0, "TAP returned an error instead of CSV"

    reader = csv.DictReader(io.StringIO(text))
    required = {name.strip() for name in spec.columns.split(",")}
    present = set(reader.fieldnames or [])
    if not required <= present:
        missing = ", ".join(sorted(required - present))
        return [], 0, f"TAP CSV is missing {missing}"

    rows: list[SolarRvRow] = []
    rejected = 0
    for record in reader:
        built = _row_from_record(record, spec)
        if built is None:
            rejected += 1
            continue
        rows.append(built)
    if len(rows) + rejected >= MAX_REC:
        logger.warning(
            "%s returned %s rows, the maxrec cap; the window may be truncated",
            product,
            MAX_REC,
        )
    return rows, rejected, None


def _row_from_record(
    record: dict[str, str | None], spec: _Instrument
) -> SolarRvRow | None:
    try:
        observed = _parse_obsdate(_cell(record, "obsdate"))
        rv = _optional_float(_cell(record, "ccfrvmod"))
        error_native = _optional_float(
            _cell(record, "dvrms" if spec.error_in == "km/s" else "e_v")
        )
        snr = _optional_float(_cell(record, "extsnr"))
        exptime = _optional_float(_cell(record, "exptime"))
        archive_jd = _optional_float(_cell(record, "ccfjdsum"))
    except (TypeError, ValueError):
        return None
    if observed is None:
        return None
    rv_m_s = None if rv is None else rv * _KM_TO_M
    if rv_m_s is not None and abs(rv_m_s) >= 5000:
        rv_m_s = None
    error_m_s = _error_m_s(error_native, spec.error_in)
    if error_m_s is not None and not 0 <= error_m_s <= 100:
        error_m_s = None
    if snr is not None and snr < 0:
        snr = None
    try:
        return SolarRvRow(
            time_tag=observed,
            instrument=spec.instrument,
            rv_m_s=rv_m_s,
            rv_error_m_s=error_m_s,
            snr=snr,
            exptime_s=exptime,
            archive_jd=archive_jd,
            archive_time_scale=spec.time_scale,
        )
    except ValidationError:
        return None


def _error_m_s(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    if unit == "km/s":
        return value * _KM_TO_M
    if unit == "cm/s":
        return value * _CM_TO_M
    raise ValueError(f"unknown RV error unit {unit}")


def _cell(record: dict[str, str | None], name: str) -> str:
    value = record.get(name)
    return "" if value is None else value


def _optional_float(value: str) -> float | None:
    text = value.strip()
    if text.lower() in _MISSING:
        return None
    return float(text)


def _parse_obsdate(value: str) -> datetime | None:
    text = value.strip()
    if text.lower() in _MISSING:
        return None
    if "." in text:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S.%f")
    else:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    return parsed.replace(tzinfo=UTC)


def _adql(spec: _Instrument, jd: float) -> str:
    """One SELECT. The table name is a constant in this module, not a request."""
    return f"SELECT {spec.columns} FROM {spec.table} WHERE obsjd > {jd:.5f}"


def fetch_solar_rv(
    client: httpx.Client,
    raw_dir: Path,
    when: datetime,
) -> list[FetchResult]:
    """POST one TAP query per instrument. Do not call this in a retry loop.

    A 429 stops the rest of this run. The next attempt is tomorrow.
    """
    jd = julian_day(when - timedelta(days=KEEP_DAYS))
    results: list[FetchResult] = []
    for spec in INSTRUMENTS:
        result = _fetch_one(client, raw_dir, when, spec, jd)
        results.append(result)
        if result.stop_run:
            break
    return results


def _fetch_one(
    client: httpx.Client,
    raw_dir: Path,
    when: datetime,
    spec: _Instrument,
    jd: float,
) -> FetchResult:
    try:
        response = client.post(
            TAP_SYNC_URL,
            data={
                "request": "doQuery",
                "lang": "ADQL",
                "format": "csv",
                "maxrec": str(MAX_REC),
                "query": _adql(spec, jd),
            },
        )
    except httpx.TransportError as exc:
        logger.error(
            "Solar RV request failed for %s (%s); next try is the scheduled run",
            spec.product,
            type(exc).__name__,
        )
        return FetchResult(spec.product, None, None, type(exc).__name__, False)

    status = response.status_code
    if status < 200 or status >= 300:
        logger.error("Solar RV %s returned HTTP %s; not retrying", spec.product, status)
        return FetchResult(spec.product, status, None, f"HTTP {status}", status == 429)

    body = response.content
    preview = body.lstrip()[:1]
    if preview in {b"<", b"F"}:
        logger.error("Solar RV %s returned an error body; not storing it", spec.product)
        return FetchResult(spec.product, status, None, "TAP error body", False)

    try:
        path = write_raw(
            raw_dir,
            when,
            spec.product,
            body,
            source_dir=SOURCE_DIR,
            suffix=".csv",
            url=TAP_SYNC_URL,
        )
    except OSError as exc:
        logger.error("Could not write raw %s: %s", spec.product, exc)
        return FetchResult(spec.product, status, None, str(exc), False)

    logger.info("Landed %s (%s bytes) at %s", spec.product, len(body), path)
    return FetchResult(spec.product, status, path, None, False)
