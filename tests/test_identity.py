"""Deterministic identity helpers tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

from zeusdb.identity import (
    ZEUSDB_NAMESPACE,
    columns_fingerprint,
    file_sha256,
    occurrence_id,
)


def test_file_sha256_known_content(tmp_path: Path):
    payload = b"zeusdb-identity-test"
    path = tmp_path / "hash.bin"
    path.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    assert file_sha256(path) == expected


def test_occurrence_id_is_deterministic():
    kwargs = {
        "source_sha256": "abc123",
        "source": "freeblock",
        "page_number": 2,
        "file_offset": 100,
        "version": 0,
        "row_id": 1,
    }
    first = occurrence_id(**kwargs)
    second = occurrence_id(**kwargs)
    assert first == second
    assert first != occurrence_id(**{**kwargs, "file_offset": 101})


def test_columns_fingerprint_blob_dict_stable():
    columns = {
        "payload": {
            "__type__": "blob",
            "encoding": "base64",
            "value": "AQID",
            "size": 3,
        }
    }
    assert columns_fingerprint(columns) == columns_fingerprint(columns)
    assert columns_fingerprint(columns) != columns_fingerprint({"payload": "other"})


def test_namespace_is_fixed():
    assert str(ZEUSDB_NAMESPACE) == "6f3a1c2e-9b4d-5e7a-8c10-2d4f6a8b0c13"
