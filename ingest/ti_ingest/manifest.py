"""Sidecar provenance for one raw landing.

A manifest is a small JSON file next to the bytes we downloaded. It
records where those bytes came from and their SHA-256, so a later run
can show the file was not edited. The hash is of the response body, not
of the manifest. SHA-256 is the hash in Python's ``hashlib``:

https://docs.python.org/3/library/hashlib.html
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

MANIFEST_SUFFIX = ".manifest.json"


def manifest_path(raw_path: Path) -> Path:
    """``<raw file>.manifest.json``, beside the landed bytes."""
    return Path(str(raw_path) + MANIFEST_SUFFIX)


def sha256_hex(body: bytes) -> str:
    """Hex SHA-256 of the exact response body."""
    return hashlib.sha256(body).hexdigest()


def write_manifest(
    raw_path: Path,
    *,
    source: str,
    product: str,
    url: str,
    retrieved_at: datetime,
    body: bytes,
) -> Path:
    """Write the sidecar after the raw file exists. Do not put secrets in ``url``."""
    if retrieved_at.tzinfo is None:
        raise ValueError("manifest timestamps must be timezone-aware")
    payload = {
        "source": source,
        "product": product,
        "url": url,
        "retrieved_at": retrieved_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": sha256_hex(body),
        "bytes": len(body),
    }
    path = manifest_path(raw_path)
    partial = Path(str(path) + ".partial")
    partial.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)
    return path
