"""Deterministic artifact identity (SHA-256 + uuid5) for ZEUS-DB."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

# 一度だけ生成して固定。以後不変。再生成禁止。
ZEUSDB_NAMESPACE = uuid.UUID("6f3a1c2e-9b4d-5e7a-8c10-2d4f6a8b0c13")

_CHUNK = 1024 * 1024  # 1 MiB chunked read for large DBs


def file_sha256(path: str | Path) -> str:
    """Compute SHA-256 of a file via chunked streaming read (read-only).

    Args:
        path: Path to the file on disk.

    Returns:
        Lowercase hex digest of the file contents.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def columns_fingerprint(columns: dict[str, Any]) -> str:
    """Stable SHA-256 fingerprint of a column dict (BLOB-dict safe)."""
    serialized = json.dumps(columns, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def aggregate_key(table_name: str, row_id: int | None, columns: dict[str, Any]) -> str:
    """Build a stable logical-record aggregation key."""
    if row_id is not None:
        return f"{table_name}|{row_id}"
    return f"{table_name}|{columns_fingerprint(columns)}"


def occurrence_id(
    *,
    source_sha256: str,
    source: str,
    page_number: int | None,
    file_offset: int | None,
    version: int | None,
    row_id: int | None,
) -> str:
    """Derive a deterministic occurrence UUID for one physical appearance."""
    name = f"{source_sha256}|{source}|{page_number}|{file_offset}|{version}|{row_id}"
    return str(uuid.uuid5(ZEUSDB_NAMESPACE, name))


def record_id(
    *,
    source_sha256: str,
    table_name: str,
    row_id: int | None,
    columns: dict[str, Any],
) -> str:
    """Derive a deterministic logical-record UUID.

    Uses row_id when available; falls back to the column fingerprint
    (required for dropped_table / __salvage__ rows that lack a row_id).
    """
    discriminator = str(row_id) if row_id is not None else columns_fingerprint(columns)
    name = f"{source_sha256}|{table_name}|{discriminator}"
    return str(uuid.uuid5(ZEUSDB_NAMESPACE, name))
