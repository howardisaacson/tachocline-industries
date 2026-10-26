"""Open the read-only Postgres session the API uses.

Compose sets ``POSTGRES_USER`` on this service to ``TI_READONLY_USER``.
The password is a keyword argument to ``connect``. It is not placed in
a URL or a log line.

psycopg is the PostgreSQL adapter for Python:
https://www.psycopg.org/psycopg3/docs/basic/usage.html
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row


class ConfigError(Exception):
    """A required environment variable is missing or not an integer."""


@dataclass(frozen=True)
class DatabaseSettings:
    """Connection settings. Inside Compose the host is the service ``db``."""

    host: str
    port: int
    user: str
    password: str
    dbname: str

    @classmethod
    def from_env(cls) -> DatabaseSettings:
        values: dict[str, str] = {}
        missing: list[str] = []
        for name in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
            value = os.environ.get(name, "").strip()
            if not value:
                missing.append(name)
            else:
                values[name] = value
        if missing:
            raise ConfigError(f"Missing environment variables: {', '.join(missing)}")
        raw_port = os.environ.get("POSTGRES_PORT", "5432").strip()
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ConfigError(f"POSTGRES_PORT is not an integer: {raw_port}") from exc
        return cls(
            host=os.environ.get("POSTGRES_HOST", "db").strip() or "db",
            port=port,
            user=values["POSTGRES_USER"],
            password=values["POSTGRES_PASSWORD"],
            dbname=values["POSTGRES_DB"],
        )


def connect(settings: DatabaseSettings) -> psycopg.Connection:
    """Open one session. The caller closes it. Rows come back as dicts."""
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        dbname=settings.dbname,
        connect_timeout=10,
        application_name="ti_api",
        row_factory=dict_row,
    )
