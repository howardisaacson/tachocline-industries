"""SELECT statements for the read-only API.

Values go through ``%s`` placeholders. A limit is a parameter, not a
piece of the SQL text, so a caller cannot change the statement by
putting SQL in the query string.
"""

SOLAR_WIND_SQL = """
SELECT time_tag, source, active,
       proton_speed, proton_density, proton_temperature
FROM solar_wind
WHERE time_tag >= %s AND time_tag < %s
ORDER BY time_tag DESC
LIMIT %s
""".strip()

SOURCES_SQL = """
SELECT source, count(*)::int AS rows, max(time_tag) AS latest
FROM solar_wind
GROUP BY source
ORDER BY source
LIMIT %s
""".strip()

INGEST_LOG_SQL = """
SELECT source, started_at, finished_at, http_status,
       rows_received, rows_upserted, rows_rejected, error
FROM ingest_log
ORDER BY finished_at DESC NULLS LAST
LIMIT %s
""".strip()

HEALTH_SQL = "SELECT 1 AS ok"
