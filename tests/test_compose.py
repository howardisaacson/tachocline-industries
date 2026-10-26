"""Issue #24 acceptance checks that do not need a running daemon.

Parsing is line-oriented on purpose: the dev requirements do not include
a YAML library, and CI does not install Docker.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def test_issue_24_services_are_present() -> None:
    for service in (
        "\n  db:\n",
        "\n  migrate:\n",
        "\n  ingest:\n",
        "\n  api:\n",
        "\n  grafana:\n",
    ):
        assert service in COMPOSE
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
    assert "127.0.0.1:${API_PORT:-8000}:8000" in COMPOSE
    assert "pg_isready" in COMPOSE


def test_compose_file_has_no_password_literal() -> None:
    assert "change-me" not in COMPOSE


def test_grafana_mounts_provisioning_and_not_the_admin_password() -> None:
    grafana = COMPOSE.split("\n  grafana:\n", 1)[1].split("\nvolumes:\n", 1)[0]
    assert "TI_READONLY_USER:" in grafana
    assert "TI_READONLY_PASSWORD:" in grafana
    assert "POSTGRES_DB:" in grafana
    assert "POSTGRES_PASSWORD:" not in grafana
    assert (
        "./dashboards/provisioning/datasources:/etc/grafana/provisioning/datasources:ro"
        in grafana
    )
    assert (
        "./dashboards/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro"
        in grafana
    )
    assert "./dashboards/json:/etc/grafana/dashboards:ro" in grafana
    assert "condition: service_completed_successfully" in grafana


def test_api_service_uses_the_readonly_role() -> None:
    """Issue #36. The API container must not receive the admin password."""
    api = COMPOSE.split("\n  api:\n", 1)[1].split("\n  grafana:\n", 1)[0]
    assert "POSTGRES_USER: ${TI_READONLY_USER:" in api
    assert "POSTGRES_PASSWORD: ${TI_READONLY_PASSWORD:" in api
    assert "${POSTGRES_PASSWORD:" not in api
    assert "context: ./api" in api
    assert "tachocline-api:0.1" in api
    assert "condition: service_completed_successfully" in api


def test_issue_25_migrations_and_readonly_env() -> None:
    names = sorted(path.name for path in (ROOT / "db" / "migrations").glob("*.sql"))
    assert names == [
        "0001_solar_wind.sql",
        "0002_goes_xray_flux.sql",
        "0003_kp_alerts.sql",
        "0004_satellite_gp.sql",
    ]
    assert "TI_READONLY_USER:" in COMPOSE
    assert "TI_READONLY_PASSWORD:" in COMPOSE
