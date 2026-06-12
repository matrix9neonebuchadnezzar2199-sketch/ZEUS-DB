"""Type-aware column conversion tests."""

from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path

import pytest

from zeusdb.engine import AnalyzeOptions, ForensicEngine
from zeusdb.output.tsv_export import export_tsv, flatten_column_value, serialize_columns_for_tsv
from zeusdb.reader.database import open_artifacts
from zeusdb.recover.convert import (
    _blob_column_value,
    _column_value,
    is_blob_column,
    normalize_sqlite_encoding,
)
from zeusdb.recover.engine import recover_live_records


@pytest.mark.parametrize(
    ("label", "expected_codec"),
    [
        ("UTF-8", "utf-8"),
        ("UTF-16le", "utf-16-le"),
        ("UTF-16be", "utf-16-be"),
        ("unknown-encoding", "utf-8"),
    ],
)
def test_normalize_sqlite_encoding(label: str, expected_codec: str):
    assert normalize_sqlite_encoding(label) == expected_codec


def test_blob_column_value_roundtrip():
    raw = b"\x00\x01\xff\xfe"
    wrapped = _blob_column_value(raw)
    assert is_blob_column(wrapped)
    assert base64.b64decode(wrapped["value"]) == raw
    assert flatten_column_value(wrapped).startswith("base64:")


def test_column_value_serial_type_blob_and_text():
    blob = _column_value(b"\xde\xad\xbe\xef", 12, "UTF-8")
    assert is_blob_column(blob)

    text = _column_value("café".encode("utf-8"), 13, "UTF-8")
    assert text == "café"


def test_column_value_utf16_text_decoding():
    payload = "テスト".encode("utf-16-le")
    serial_type = 13 + len(payload)
    decoded = _column_value(payload, serial_type, "UTF-16le")
    assert decoded == "テスト"


def test_utf16le_database_live_records(tmp_path: Path):
    db_path = tmp_path / "utf16le.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA encoding = 'UTF-16le'")
    conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO messages (body) VALUES (?)", ("Unicodeテスト",))
    conn.commit()
    conn.close()

    bundle = open_artifacts(db_path)
    try:
        assert normalize_sqlite_encoding(bundle.encoding) == "utf-16-le"
        records = recover_live_records(bundle, ["messages"])
    finally:
        from zeusdb.reader.database import close_artifacts

        close_artifacts(bundle)

    assert len(records) == 1
    assert records[0].columns["body"] == "Unicodeテスト"


def test_blob_database_live_records(tmp_path: Path):
    db_path = tmp_path / "blobcase.db"
    payload = b"\x89PNG\r\n\x1a\n"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY, data BLOB)")
    conn.execute("INSERT INTO assets (data) VALUES (?)", (payload,))
    conn.commit()
    conn.close()

    bundle = open_artifacts(db_path)
    try:
        records = recover_live_records(bundle, ["assets"])
    finally:
        from zeusdb.reader.database import close_artifacts

        close_artifacts(bundle)

    assert len(records) == 1
    blob = records[0].columns["data"]
    assert is_blob_column(blob)
    assert base64.b64decode(blob["value"]) == payload


def test_tsv_export_flattens_blob(sample_db, tmp_path: Path):
    db_path = tmp_path / "blob.tsv.db"
    payload = b"\x01\x02\x03"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, content BLOB)")
    conn.execute("INSERT INTO files (content) VALUES (?)", (payload,))
    conn.commit()
    conn.close()

    result = ForensicEngine().analyze(db_path, AnalyzeOptions(carve=False))
    tsv_path = export_tsv(result, tmp_path / "out.tsv")
    import csv

    with tsv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) >= 1
    parsed = json.loads(rows[0]["columns_json"])
    assert parsed["content"].startswith("base64:")
    assert base64.b64decode(parsed["content"].removeprefix("base64:")) == payload


def test_serialize_columns_for_tsv_preserves_non_blob():
    serialized = serialize_columns_for_tsv({"name": "Alice", "note": "ok"})
    assert json.loads(serialized) == {"name": "Alice", "note": "ok"}
