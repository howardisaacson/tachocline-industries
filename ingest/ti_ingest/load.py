"""Validate a landed SWPC file and upsert it into Postgres.

An upsert is an insert that updates the existing row when the natural
key is already there, instead of failing or adding a second copy. The
key is ``(time_tag, source)``: one minute, one spacecraft. PostgreSQL
writes that as ``INSERT … ON CONFLICT DO UPDATE``. Running the same raw
file again replaces those rows in place.

https://www.postgresql.org/docs/current/sql-insert.html

Values go through ``%s`` placeholders. The spacecraft id is data, not
part of the SQL text.

One ``ingest_log`` row is written per file this run actually attempted.
Wind and mag are separate feeds, and ``ingest_log.source`` is the feed
name (``rtsw_wind_1m``), so one scheduled tick writes two log rows when
both files are fetched. A 429 that skips mag does not invent a mag row.
The GOES X-ray job is its own tick and logs ``xrays-6-hour``. The
conflict key for that table is ``(time_tag, satellite, energy)``.
The Kp and alerts job is its own tick. It logs
``planetary_k_index_1m``, ``noaa-planetary-k-index``, and ``alerts``.
Kp conflicts on ``time_tag``. Alerts conflict on
``(issue_datetime, product_id)``.
The CelesTrak job is its own tick, every two hours. It logs one
``gp-<norad_cat_id>`` source per catalog number and conflicts on
``(epoch, norad_cat_id)``.
``error`` is set when the file was not loaded. Rows that fail validation
increment ``rows_rejected`` and leave ``error`` empty: the file was
readable, and the count is the signal.

The upsert and its log row commit together. A failure rolls that work
back, then a second short transaction records the error.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, Self

from pydantic import ValidationError

from ti_ingest.celestrak_gp import CATALOG_NUMBERS
from ti_ingest.models import (
    AlertRow,
    GpRow,
    Kp1mRow,
    Kp3hRow,
    MagRow,
    StoredRow,
    WindRow,
    XrayRow,
)
from ti_ingest.swpc import FetchResult

logger = logging.getLogger(__name__)

# Placeholders stay in this order. Tests and the INSERT both use these strings.
WIND_UPSERT = """
INSERT INTO solar_wind (
    time_tag, source, active,
    proton_speed, proton_density, proton_temperature
) VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (time_tag, source) DO UPDATE SET
    active = EXCLUDED.active,
    proton_speed = EXCLUDED.proton_speed,
    proton_density = EXCLUDED.proton_density,
    proton_temperature = EXCLUDED.proton_temperature
""".strip()

MAG_UPSERT = """
INSERT INTO rtsw_mag_1m (
    time_tag, source, active,
    bt, bx_gse, by_gse, bz_gse, bx_gsm, by_gsm, bz_gsm
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (time_tag, source) DO UPDATE SET
    active = EXCLUDED.active,
    bt = EXCLUDED.bt,
    bx_gse = EXCLUDED.bx_gse,
    by_gse = EXCLUDED.by_gse,
    bz_gse = EXCLUDED.bz_gse,
    bx_gsm = EXCLUDED.bx_gsm,
    by_gsm = EXCLUDED.by_gsm,
    bz_gsm = EXCLUDED.bz_gsm
""".strip()

INGEST_LOG_SQL = """
INSERT INTO ingest_log (
    source, started_at, finished_at, http_status,
    rows_received, rows_upserted, rows_rejected, error
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
""".strip()

XRAY_UPSERT = """
INSERT INTO goes_xray_flux (
    time_tag, satellite, energy,
    flux, observed_flux, electron_correction, electron_contamination
) VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (time_tag, satellite, energy) DO UPDATE SET
    flux = EXCLUDED.flux,
    observed_flux = EXCLUDED.observed_flux,
    electron_correction = EXCLUDED.electron_correction,
    electron_contamination = EXCLUDED.electron_contamination
""".strip()

KP_1M_UPSERT = """
INSERT INTO planetary_kp_1m (
    time_tag, kp_index, estimated_kp, kp
) VALUES (%s, %s, %s, %s)
ON CONFLICT (time_tag) DO UPDATE SET
    kp_index = EXCLUDED.kp_index,
    estimated_kp = EXCLUDED.estimated_kp,
    kp = EXCLUDED.kp
""".strip()

KP_3H_UPSERT = """
INSERT INTO planetary_kp_3h (
    time_tag, kp, a_running, station_count
) VALUES (%s, %s, %s, %s)
ON CONFLICT (time_tag) DO UPDATE SET
    kp = EXCLUDED.kp,
    a_running = EXCLUDED.a_running,
    station_count = EXCLUDED.station_count
""".strip()

ALERT_UPSERT = """
INSERT INTO swpc_alert (
    issue_datetime, product_id, message
) VALUES (%s, %s, %s)
ON CONFLICT (issue_datetime, product_id) DO UPDATE SET
    message = EXCLUDED.message
""".strip()

GP_UPSERT = """
INSERT INTO satellite_gp (
    epoch, norad_cat_id, object_name, object_id,
    mean_motion, eccentricity, inclination, ra_of_asc_node,
    arg_of_pericenter, mean_anomaly, bstar, mean_motion_dot,
    perigee_altitude_km, apogee_altitude_km
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (epoch, norad_cat_id) DO UPDATE SET
    object_name = EXCLUDED.object_name,
    object_id = EXCLUDED.object_id,
    mean_motion = EXCLUDED.mean_motion,
    eccentricity = EXCLUDED.eccentricity,
    inclination = EXCLUDED.inclination,
    ra_of_asc_node = EXCLUDED.ra_of_asc_node,
    arg_of_pericenter = EXCLUDED.arg_of_pericenter,
    mean_anomaly = EXCLUDED.mean_anomaly,
    bstar = EXCLUDED.bstar,
    mean_motion_dot = EXCLUDED.mean_motion_dot,
    perigee_altitude_km = EXCLUDED.perigee_altitude_km,
    apogee_altitude_km = EXCLUDED.apogee_altitude_km
""".strip()

_UPSERTS: dict[str, tuple[type[StoredRow], str]] = {
    "rtsw_wind_1m": (WindRow, WIND_UPSERT),
    "rtsw_mag_1m": (MagRow, MAG_UPSERT),
    "xrays-6-hour": (XrayRow, XRAY_UPSERT),
    "planetary_k_index_1m": (Kp1mRow, KP_1M_UPSERT),
    "noaa-planetary-k-index": (Kp3hRow, KP_3H_UPSERT),
    "alerts": (AlertRow, ALERT_UPSERT),
}
# One feed name per catalog number, all using the same INSERT.
_UPSERTS.update({f"gp-{catnr}": (GpRow, GP_UPSERT) for catnr in CATALOG_NUMBERS})

_ERROR_LIMIT = 500


class DBCursor(Protocol):
    """The cursor methods this loader uses. psycopg's cursor provides them."""

    def execute(self, query: str, params: Sequence[object] = ()) -> object: ...

    def executemany(
        self, query: str, params_seq: Sequence[Sequence[object]]
    ) -> object: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *args: object) -> None: ...


class DBConnection(Protocol):
    """Commit publishes the transaction. Rollback throws it away."""

    def cursor(self) -> DBCursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class ParsedFile:
    """``parse_error`` is set only when the file itself could not be read."""

    received: int
    rows: tuple[StoredRow, ...]
    rejected: int
    parse_error: str | None


def parse_body(product: str, model: type[StoredRow], body: bytes) -> ParsedFile:
    """Split one raw file into valid rows and a reject count.

    Does not touch the database. The bytes are the landed file, unchanged.
    """
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return ParsedFile(0, (), 0, _clip(f"{type(exc).__name__}: {exc}"))
    if not isinstance(payload, list):
        return ParsedFile(0, (), 0, "SWPC body is not a JSON array")

    rows: list[StoredRow] = []
    reasons: set[str] = set()
    for item in payload:
        try:
            rows.append(model.model_validate(item))
        except ValidationError as exc:
            err = exc.errors()[0]
            loc = ".".join(str(part) for part in err["loc"]) or "<row>"
            reasons.add(f"{loc}: {err['type']}")
    rejected = len(payload) - len(rows)
    if reasons:
        logger.warning(
            "Rejected %s %s row(s): %s",
            rejected,
            product,
            "; ".join(sorted(reasons)),
        )
    return ParsedFile(len(payload), tuple(rows), rejected, None)


def store_fetch(
    conn: DBConnection, fetch: FetchResult, *, started_at: datetime
) -> None:
    """Upsert one attempted file and write its ``ingest_log`` row.

    ``rows_upserted`` counts validated rows sent to the database, including
    a conflict that updated an existing minute. It is not "new keys only".
    """
    if fetch.path is None:
        _record(
            conn,
            product=fetch.product,
            started_at=started_at,
            http_status=fetch.status_code,
            received=0,
            upserted=0,
            rejected=0,
            error=fetch.error,
        )
        return

    spec = _UPSERTS.get(fetch.product)
    if spec is None:
        _record(
            conn,
            product=fetch.product,
            started_at=started_at,
            http_status=fetch.status_code,
            received=0,
            upserted=0,
            rejected=0,
            error=f"unknown product {fetch.product}",
        )
        return

    model, sql = spec
    try:
        body = fetch.path.read_bytes()
    except OSError as exc:
        _record(
            conn,
            product=fetch.product,
            started_at=started_at,
            http_status=fetch.status_code,
            received=0,
            upserted=0,
            rejected=0,
            error=_clip(f"OSError: {exc}"),
        )
        return

    parsed = parse_body(fetch.product, model, body)
    if parsed.parse_error is not None:
        _record(
            conn,
            product=fetch.product,
            started_at=started_at,
            http_status=fetch.status_code,
            received=parsed.received,
            upserted=0,
            rejected=parsed.rejected,
            error=parsed.parse_error,
        )
        return

    params = _log_params(
        product=fetch.product,
        started_at=started_at,
        http_status=fetch.status_code,
        received=parsed.received,
        upserted=len(parsed.rows),
        rejected=parsed.rejected,
        error=None,
    )
    try:
        with conn.cursor() as cur:
            if parsed.rows:
                cur.executemany(sql, [row.as_params() for row in parsed.rows])
            cur.execute(INGEST_LOG_SQL, params)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.exception("Upsert failed for %s", fetch.product)
        _record(
            conn,
            product=fetch.product,
            started_at=started_at,
            http_status=fetch.status_code,
            received=parsed.received,
            upserted=0,
            rejected=parsed.rejected,
            error=_clip(f"{type(exc).__name__}: {exc}"),
        )
        return
    _log_line(params)


def _record(
    conn: DBConnection,
    *,
    product: str,
    started_at: datetime,
    http_status: int | None,
    received: int,
    upserted: int,
    rejected: int,
    error: str | None,
) -> None:
    """Commit one log row of its own. Used when there is nothing to upsert."""
    params = _log_params(
        product=product,
        started_at=started_at,
        http_status=http_status,
        received=received,
        upserted=upserted,
        rejected=rejected,
        error=error,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(INGEST_LOG_SQL, params)
        conn.commit()
    except Exception:
        logger.exception("Could not write ingest_log for %s", product)
        conn.rollback()
        return
    _log_line(params)


def _log_params(
    *,
    product: str,
    started_at: datetime,
    http_status: int | None,
    received: int,
    upserted: int,
    rejected: int,
    error: str | None,
) -> tuple[object, ...]:
    return (
        product,
        started_at,
        datetime.now(UTC),
        http_status,
        received,
        upserted,
        rejected,
        error,
    )


def _log_line(params: tuple[object, ...]) -> None:
    product, _, _, http_status, received, upserted, rejected, error = params
    logger.info(
        "%s http=%s received=%s upserted=%s rejected=%s error=%s",
        product,
        http_status,
        received,
        upserted,
        rejected,
        error,
    )


def _clip(message: str) -> str:
    if len(message) <= _ERROR_LIMIT:
        return message
    return message[:_ERROR_LIMIT]
