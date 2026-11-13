# Image shared by the migrate and ingest services (ADR 0014).
# migrate applies SQL. ingest fetches SWPC files and upserts them.
# linux/amd64 and linux/arm64/v8, checked 2026-11-13. No platform pin.
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

# `app` is the account the entrypoint setuids to. 1000 is only the
# fallback for migrate, which does not mount the landing zone. Ingest
# points this account at the owner of /data/raw (ADR 0029). There is
# no USER instruction: the entrypoint must start as root to call setuid.
# Bytecode is not written next to the source, because /app may stay
# owned by the build-time uid after that switch.
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "-m", "ti_ingest.entrypoint"]
CMD ["python", "-m", "ti_ingest"]
