# Image shared by the migrate and ingest services (ADR 0014).
# migrate applies SQL. ingest fetches SWPC files and upserts them.
FROM python:3.12-slim-bookworm

# Logs appear immediately instead of waiting for a full buffer.
ENV PYTHONUNBUFFERED=1

# psql applies SQL files (ADR 0019). Bookworm's client is Postgres 15;
# it can still run scripts against the Postgres 17 server.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin --uid 1000 app

WORKDIR /app
COPY --chown=app:app requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app ti_ingest ./ti_ingest

# uid 1000 matches a typical laptop user, so files under data/raw stay
# editable on the host. The poller writes only that mounted directory.
USER app
CMD ["python", "-m", "ti_ingest"]
