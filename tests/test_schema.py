"""Issue #25 schema checks. They read the SQL file and do not start Postgres."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLAR = (ROOT / "db" / "migrations" / "0001_solar_wind.sql").read_text(encoding="utf-8")

# SWPC keys documented in docs/research/data_sources.md and confirmed on the
# live rtsw files. Names we did not document (quality flags, alphas) stay out.
WIND_COLUMNS = (
    "time_tag",
    "source",
    "active",
    "proton_speed",
    "proton_density",
    "proton_temperature",
)
MAG_COLUMNS = (
    "time_tag",
    "source",
    "active",
    "bt",
    "bx_gse",
    "by_gse",
    "bz_gse",
    "bx_gsm",
    "by_gsm",
    "bz_gsm",
)
# ADR 0004: source, start/end, HTTP status, rows received/upserted/rejected, error.
LOG_COLUMNS = (
    "source",
    "started_at",
    "finished_at",
    "http_status",
    "rows_received",
    "rows_upserted",
    "rows_rejected",
    "error",
)


def test_migration_stays_one_transaction() -> None:
    # The runner opens the transaction. A BEGIN in the file would commit early.
    assert "\nBEGIN" not in SOLAR
    assert "\nCOMMIT" not in SOLAR


def test_hypertables_use_the_documented_natural_key() -> None:
    assert SOLAR.count("PRIMARY KEY (time_tag, source)") == 2
    assert "create_hypertable(\n    'solar_wind'," in SOLAR
    assert "create_hypertable(\n    'rtsw_mag_1m'," in SOLAR
    assert "CREATE TABLE ingest_log" in SOLAR
    # Run health is a small table, not a measurement hypertable.
    assert "create_hypertable(\n    'ingest_log'" not in SOLAR
    for column in WIND_COLUMNS + MAG_COLUMNS + LOG_COLUMNS:
        assert column in SOLAR


def test_goes_xray_migration_adds_a_table_and_a_grant() -> None:
    """Issue #31. 0001 is unchanged. The new file does not create a role."""
    sql = (ROOT / "db" / "migrations" / "0002_goes_xray_flux.sql").read_text(
        encoding="utf-8"
    )
    assert "\nBEGIN" not in sql
    assert "\nCOMMIT" not in sql
    assert "CREATE TABLE goes_xray_flux" in sql
    assert "PRIMARY KEY (time_tag, satellite, energy)" in sql
    assert "create_hypertable(\n    'goes_xray_flux'," in sql
    assert "CREATE ROLE" not in sql
    assert "CREATE EXTENSION" not in sql
    assert "GRANT SELECT ON TABLE goes_xray_flux" in sql
    grant = sql.split("GRANT SELECT ON TABLE", 1)[1]
    assert "goes_xray_flux" in grant
    assert "schema_migrations" not in grant
    assert "change-me" not in sql
    assert "electron_contaminaton" in sql
    assert "double precision" in sql


def test_readonly_role_does_not_embed_a_password() -> None:
    assert "CREATE ROLE" in SOLAR
    assert "GRANT SELECT ON TABLE" in SOLAR
    grant = SOLAR.split("GRANT SELECT ON TABLE", 1)[1]
    assert "solar_wind" in grant
    assert "rtsw_mag_1m" in grant
    assert "ingest_log" in grant
    assert "schema_migrations" not in grant
    assert "PASSWORD :'ti_readonly_password'" in SOLAR
    assert "\\getenv ti_readonly_password TI_READONLY_PASSWORD" in SOLAR
    assert "change-me" not in SOLAR
