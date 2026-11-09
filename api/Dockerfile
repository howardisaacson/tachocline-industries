# Read-only API image (ADR 0006, ADR 0014). Separate from the ingest
# image so a poller crash does not take the HTTP server down, and so
# this container does not ship the poller code.
# 3.15.2 is the 2026-10-25 security release. The floating 3.15 tag moves,
# so the patch is pinned (ADR 0038). Bookworm stays; only the interpreter changes.
FROM python:3.15.2-slim-bookworm

ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /usr/sbin/nologin --uid 1000 app

WORKDIR /app
COPY --chown=app:app requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app ti_api ./ti_api

USER app
EXPOSE 8000
CMD ["uvicorn", "ti_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
