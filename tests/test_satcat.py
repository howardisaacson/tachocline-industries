"""SATCAT decay records and the raw-file manifest. HTTP is a fake."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx

from ti_ingest.celestrak_gp import CATALOG_NUMBERS
from ti_ingest.gfz_kp import FILE_URL, fetch_gfz
from ti_ingest.manifest import manifest_path, sha256_hex
from ti_ingest.satcat import poll_satcat, record_url
from ti_ingest.swpc import make_client

WHEN = datetime(2026, 11, 1, 18, tzinfo=UTC)


def test_satcat_lands_each_catalog_number_with_a_manifest(tmp_path) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        catnr = int(request.url.params["CATNR"])
        body = json.dumps(
            [
                {
                    "NORAD_CAT_ID": catnr,
                    "OBJECT_NAME": "TEST",
                    "DECAY_DATE": "",
                }
            ]
        ).encode()
        return httpx.Response(200, content=body)

    with make_client(
        "TachoclineIndustries/0.1 (test)",
        transport=httpx.MockTransport(handler),
    ) as client:
        results = poll_satcat(client, tmp_path, now=WHEN)

    assert [item.product for item in results] == [
        f"satcat-{catnr}" for catnr in CATALOG_NUMBERS
    ]
    assert seen == [record_url(catnr) for catnr in CATALOG_NUMBERS]
    assert results[0].path is not None
    sidecar = manifest_path(results[0].path)
    record = json.loads(sidecar.read_text(encoding="utf-8"))
    body = results[0].path.read_bytes()
    assert record["url"] == record_url(CATALOG_NUMBERS[0])
    assert record["retrieved_at"] == "2026-11-01T18:00:00Z"
    assert record["sha256"] == sha256_hex(body)
    assert record["source"] == "satcat"
    assert record["bytes"] == len(body)


def test_satcat_stops_on_429(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, content=b"slow down")

    with make_client("test", transport=httpx.MockTransport(handler)) as client:
        results = poll_satcat(client, tmp_path, now=WHEN)

    assert len(results) == 1
    assert results[0].stop_run is True
    assert list(tmp_path.rglob("*.json")) == []


def test_gfz_file_gets_a_manifest(tmp_path) -> None:
    body = b"2026 10 27 example file\n"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == FILE_URL
        return httpx.Response(200, content=body)

    with make_client("test", transport=httpx.MockTransport(handler)) as client:
        result = fetch_gfz(client, tmp_path, WHEN)

    assert result.path is not None
    assert result.path.suffix == ".txt"
    record = json.loads(manifest_path(result.path).read_text(encoding="utf-8"))
    assert record["url"] == FILE_URL
    assert record["sha256"] == sha256_hex(body)
    assert record["source"] == "gfz_kp"
    assert record["product"] == "gfz-kp-3h"
