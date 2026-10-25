"""Open the Postgres connection the poller upserts into.

The host, port, user, password, and database name are the same
environment variables the migrate container already uses. Inside
Compose the host is the service name ``db``, not the laptop. The
password is a keyword argument to ``connect``. It is not placed in a
URL or a log line.

psycopg is the PostgreSQL adapter for Python:
https://www.psycopg.org/psycopg3/docs/basic/usage.html
"""

from __future__ import annotations

import psycopg

from ti_ingest.migrate import DatabaseSettings


def connect(settings: DatabaseSettings) -> psycopg.Connection:
    """Open one session. The caller closes it."""
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        dbname=settings.dbname,
        connect_timeout=10,
        application_name="ti_ingest",
    )
