"""Migration runner tests. They do not start Postgres or call psql."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from ti_ingest.migrate import (
    CommandResult,
    ConfigError,
    DatabaseSettings,
    MigrationError,
    apply_file_args,
    apply_pending,
    migration_files,
    psql_env,
    subprocess_runner,
    wait_for_database,
)


class FakeRunner:
    """Records psql argument lists and pretends the bookkeeping table exists."""

    def __init__(
        self, applied: set[str] | None = None, fail_on: str | None = None
    ) -> None:
        self.applied = set(applied or ())
        self.fail_on = fail_on
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> CommandResult:
        self.calls.append(args)
        if len(args) >= 3 and "SELECT filename" in args[2]:
            stdout = "".join(f"{name}\n" for name in sorted(self.applied))
            return CommandResult(0, stdout, "")
        if self.fail_on is not None and any(self.fail_on in part for part in args):
            return CommandResult(1, "", f"syntax error in {self.fail_on}")
        if "-f" in args:
            variable = args[args.index("-v") + 1]
            self.applied.add(variable.split("=", 1)[1])
        return CommandResult(0, "", "")


def _write(directory: Path, name: str) -> None:
    (directory / name).write_text("SELECT 1;\n", encoding="utf-8")


def test_files_sort_by_numeric_prefix_not_spelling(tmp_path: Path) -> None:
    # Spelling order would run 00010 before 0002, because "1" < "2".
    for name in ("0002_b.sql", "00010_c.sql", "0001_a.sql"):
        _write(tmp_path, name)
    assert [path.name for path in migration_files(tmp_path)] == [
        "0001_a.sql",
        "0002_b.sql",
        "00010_c.sql",
    ]


def test_wrong_sql_name_is_ignored(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write(tmp_path, "not-a-migration.sql")
    _write(tmp_path, "0001_ok.sql")
    (tmp_path / ".gitkeep").write_text("keep\n", encoding="utf-8")
    fake = FakeRunner()
    with caplog.at_level(logging.WARNING):
        applied = apply_pending(tmp_path, fake)
    assert applied == ["0001_ok.sql"]
    assert "not-a-migration.sql" in caplog.text


def test_empty_directory_creates_bookkeeping_and_applies_nothing(
    tmp_path: Path,
) -> None:
    fake = FakeRunner()
    assert apply_pending(tmp_path, fake) == []
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in fake.calls[0][1]
    assert not any("-f" in call for call in fake.calls)


def test_skips_filenames_already_recorded(tmp_path: Path) -> None:
    _write(tmp_path, "0001_a.sql")
    _write(tmp_path, "0002_b.sql")
    fake = FakeRunner(applied={"0001_a.sql"})
    assert apply_pending(tmp_path, fake) == ["0002_b.sql"]
    file_calls = [call for call in fake.calls if "-f" in call]
    assert len(file_calls) == 1
    assert file_calls[0][0] == "-1"
    assert str(tmp_path / "0002_b.sql") in file_calls[0]


def test_failure_does_not_apply_later_files(tmp_path: Path) -> None:
    for name in ("0001_a.sql", "0002_b.sql", "0003_c.sql"):
        _write(tmp_path, name)
    fake = FakeRunner(fail_on="0002_b.sql")
    with pytest.raises(MigrationError, match="0002_b.sql"):
        apply_pending(tmp_path, fake)
    assert "0001_a.sql" in fake.applied
    assert "0002_b.sql" not in fake.applied
    assert not any("0003_c.sql" in part for call in fake.calls for part in call)


def test_missing_directory_does_not_run_sql(tmp_path: Path) -> None:
    fake = FakeRunner()
    with pytest.raises(MigrationError, match="does not exist"):
        apply_pending(tmp_path / "missing", fake)
    assert fake.calls == []


def test_apply_args_quote_the_filename_instead_of_concatenating(tmp_path: Path) -> None:
    args = apply_file_args(tmp_path / "0001_init.sql")
    assert "s3cret" not in args
    assert (
        "INSERT INTO schema_migrations (filename) VALUES (:'ti_migration_filename')"
        in args
    )
    assert "ti_migration_filename=0001_init.sql" in args


def test_password_is_in_the_environment_not_the_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_USER", "ti_admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret-value")
    monkeypatch.setenv("POSTGRES_DB", "tachocline")
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    settings = DatabaseSettings.from_env()
    env = psql_env(settings, base={"PATH": "/usr/bin"})
    assert env["PGPASSWORD"] == "s3cret-value"
    assert env["PGHOST"] == "db"
    assert env["PGPORT"] == "5432"
    assert "s3cret-value" not in " ".join(apply_file_args(Path("0001_init.sql")))


def test_runner_does_not_use_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("POSTGRES_USER", "ti_admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret-value")
    monkeypatch.setenv("POSTGRES_DB", "tachocline")
    settings = DatabaseSettings.from_env()
    subprocess_runner(settings)(["-c", "SELECT 1"])
    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs.get("shell", False) is False
    cmd = seen["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "psql"
    assert "s3cret-value" not in cmd
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["PGPASSWORD"] == "s3cret-value"


def test_missing_password_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "ti_admin")
    monkeypatch.setenv("POSTGRES_DB", "tachocline")
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    with pytest.raises(ConfigError, match="POSTGRES_PASSWORD"):
        DatabaseSettings.from_env()


def test_bad_port_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "ti_admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret-value")
    monkeypatch.setenv("POSTGRES_DB", "tachocline")
    monkeypatch.setenv("POSTGRES_PORT", "not-a-port")
    with pytest.raises(ConfigError, match="POSTGRES_PORT"):
        DatabaseSettings.from_env()


def test_wait_retries_then_succeeds() -> None:
    attempts = {"n": 0}
    sleeps: list[float] = []

    def run(_args: list[str]) -> CommandResult:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return CommandResult(1, "", "connection refused")
        return CommandResult(0, "1\n", "")

    wait_for_database(run, attempts=5, pause=sleeps.append)
    assert attempts["n"] == 3
    assert sleeps == [1, 1]


def test_wait_gives_up_without_retrying_forever() -> None:
    calls = {"n": 0}

    def run(_args: list[str]) -> CommandResult:
        calls["n"] += 1
        return CommandResult(1, "", "nope")

    with pytest.raises(MigrationError, match="nope"):
        wait_for_database(run, attempts=2, pause=lambda _seconds: None)
    assert calls["n"] == 2
