"""Apply numbered SQL files once, then exit.

A migration file is named like ``0001_short_name.sql``. Files run in
numeric order (``0002`` before ``00010``). Each file is one ``psql``
transaction. The filename is inserted in that same transaction, so a
failure does not count as applied.

``schema_migrations`` is this runner's bookkeeping table. The solar-wind
tables are issue #25. See ADR 0019.

The database password is ``PGPASSWORD``. It is not a ``psql`` argument,
because arguments can show up in ``ps`` output.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Leading digits, an underscore, then a short name. Dollar-quote bodies
# stay inside the file; we never split on semicolons.
MIGRATION_RE = re.compile(r"^(\d+)_([A-Za-z0-9_]+)\.sql$")

ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
)
""".strip()

LIST_SQL = "SELECT filename FROM schema_migrations ORDER BY filename"


class MigrationError(Exception):
    """A migration file failed, or the database could not be used."""


class ConfigError(Exception):
    """A required environment variable is missing or not an integer."""


@dataclass(frozen=True)
class DatabaseSettings:
    """Connection settings for the migrate container.

    ``host`` inside Compose is the service name ``db``. ``POSTGRES_PORT``
    in ``.env`` is the port published on the laptop; this process uses the
    port Postgres listens on inside the network (5432 unless overridden).
    """

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


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str]], CommandResult]


def psql_env(
    settings: DatabaseSettings, base: dict[str, str] | None = None
) -> dict[str, str]:
    """Environment for ``psql``. Password stays here, not in argv."""
    env = dict(os.environ if base is None else base)
    env["PGHOST"] = settings.host
    env["PGPORT"] = str(settings.port)
    env["PGUSER"] = settings.user
    env["PGPASSWORD"] = settings.password
    env["PGDATABASE"] = settings.dbname
    return env


def subprocess_runner(settings: DatabaseSettings) -> CommandRunner:
    """Run ``psql`` with ``ON_ERROR_STOP`` so a bad statement fails the file."""
    env = psql_env(settings)

    def run(args: list[str]) -> CommandResult:
        completed = subprocess.run(
            ["psql", "-X", "-v", "ON_ERROR_STOP=1", *args],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)

    return run


def migration_files(directory: Path) -> list[Path]:
    """Return SQL migrations in numeric order.

    A ``.sql`` file whose name does not match is ignored and logged.
    ``.gitkeep`` is not SQL, so it is skipped quietly.
    """
    if not directory.is_dir():
        raise MigrationError(f"migrations directory does not exist: {directory}")
    matched: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        match = MIGRATION_RE.match(path.name)
        if match:
            matched.append((int(match.group(1)), path))
        elif path.suffix == ".sql":
            logger.warning(
                "Ignoring %s; expected a name like 0001_short_name.sql", path.name
            )
    matched.sort(key=lambda item: (item[0], item[1].name))
    return [path for _, path in matched]


def apply_file_args(path: Path) -> list[str]:
    """``psql`` args that apply one file and record it in one transaction.

    ``-1`` wraps every command in BEGIN/COMMIT. ``:'ti_migration_filename'``
    inserts the name as a quoted SQL literal. The variable name is long so
    a migration that happens to contain ``:filename`` is not rewritten:
    psql substitutes every set variable it sees in the file.
    """
    return [
        "-1",
        "-v",
        f"ti_migration_filename={path.name}",
        "-f",
        str(path),
        "-c",
        "INSERT INTO schema_migrations (filename) VALUES (:'ti_migration_filename')",
    ]


def _check(result: CommandResult, context: str) -> None:
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "psql failed"
        raise MigrationError(f"{context}: {detail}")


def applied_filenames(run: CommandRunner) -> set[str]:
    result = run(["-tA", "-c", LIST_SQL])
    _check(result, "could not list applied migrations")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def apply_pending(directory: Path, run: CommandRunner) -> list[str]:
    """Apply files that are not in ``schema_migrations``. Return new names.

    Listing the directory happens before any SQL, so a wrong path does
    not create the bookkeeping table.
    """
    files = migration_files(directory)
    _check(run(["-c", ENSURE_SQL]), "could not create schema_migrations")
    done = applied_filenames(run)
    applied_now: list[str] = []
    for path in files:
        if path.name in done:
            logger.info("Already applied %s", path.name)
            continue
        logger.info("Applying %s", path.name)
        _check(run(apply_file_args(path)), f"migration failed: {path.name}")
        applied_now.append(path.name)
    if not applied_now:
        logger.info("No pending migrations")
    return applied_now


def wait_for_database(
    run: CommandRunner,
    attempts: int = 10,
    pause: Callable[[float], None] = time.sleep,
) -> None:
    """Retry ``SELECT 1`` until Postgres accepts connections.

    The Compose healthcheck usually makes the first try succeed. The
    retry covers the gap between "ready" and this container starting.
    A failed migration is not retried; only this probe is.
    """
    last = ""
    for attempt in range(1, attempts + 1):
        result = run(["-tA", "-c", "SELECT 1"])
        if result.returncode == 0:
            return
        last = result.stderr.strip() or "connection failed"
        if attempt < attempts:
            pause(1)
    raise MigrationError(f"database did not accept connections: {last}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    directory = Path(os.environ.get("MIGRATIONS_DIR", "/migrations"))
    try:
        settings = DatabaseSettings.from_env()
        run = subprocess_runner(settings)
        wait_for_database(run)
        apply_pending(directory, run)
    except (ConfigError, MigrationError) as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
