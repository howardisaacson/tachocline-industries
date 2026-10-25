"""Issue #24 acceptance checks that do not need a running daemon.

Parsing is line-oriented on purpose: the dev requirements do not include
a YAML library, and CI does not install Docker.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def test_issue_24_services_are_present() -> None:
    for service in ("\n  db:\n", "\n  migrate:\n", "\n  ingest:\n", "\n  grafana:\n"):
        assert service in COMPOSE
    assert "\n  api:\n" not in COMPOSE
    assert "timescale/timescaledb:2.31.0-pg17-oss" in COMPOSE
    assert "grafana/grafana:13.2.4" in COMPOSE


def test_database_data_is_a_named_volume() -> None:
    assert "pgdata:/var/lib/postgresql/data" in COMPOSE
    assert "grafana_data:/var/lib/grafana" in COMPOSE
    assert "./pgdata" not in COMPOSE
    assert "./grafana" not in COMPOSE
    # Landing zone (ADR 0004), not the database files.
    assert "./data/raw:/data/raw" in COMPOSE


def test_startup_order_and_localhost_ports() -> None:
    assert "condition: service_healthy" in COMPOSE
    assert "condition: service_completed_successfully" in COMPOSE
    assert 'restart: "no"' in COMPOSE
    assert "127.0.0.1:${POSTGRES_PORT:" in COMPOSE
    assert "127.0.0.1:${GRAFANA_PORT:" in COMPOSE
    assert "pg_isready" in COMPOSE


def test_compose_file_has_no_password_literal() -> None:
    assert "change-me" not in COMPOSE
    assert "dashboards/" not in COMPOSE


def test_no_numbered_sql_until_issue_25() -> None:
    sql_files = list((ROOT / "db" / "migrations").glob("*.sql"))
    assert sql_files == []
