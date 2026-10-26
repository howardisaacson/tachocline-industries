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

from ti_ingest.models import MagRow, SwpcRow, WindRow
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

_UPSERTS: dict[str, tuple[type[SwpcRow], str]] = {
    "rtsw_wind_1m": (WindRow, WIND_UPSERT),
    "rtsw_mag_1m": (MagRow, MAG_UPSERT),
}

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
    rows: tuple[SwpcRow, ...]
    rejected: int
    parse_error: str | None


def parse_body(product: str, model: type[SwpcRow], body: bytes) -> ParsedFile:
    """Split one raw file into valid rows and a reject count.

    Does not touch the database. The bytes are the landed file, unchanged.
    """
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return ParsedFile(0, (), 0, _clip(f"{type(exc).__name__}: {exc}"))
    if not isinstance(payload, list):
        return ParsedFile(0, (), 0, "SWPC body is not a JSON array")

    rows: list[SwpcRow] = []
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
