"""Dedupe behavior tests."""

from __future__ import annotations

from zeusdb.models import NormalizedRecord, Provenance, RecordSource
from zeusdb.recover.engine import _dedupe_records


def _sample_record(
    *,
    page_number: int | None,
    file_offset: int | None,
    version: int | None = 0,
    row_id: int = 1,
    columns: dict | None = None,
) -> NormalizedRecord:
    return NormalizedRecord(
        table_name="users",
        row_id=row_id,
        columns=columns or {"name": "Alice"},
        is_live=False,
        is_deleted=True,
        provenance=Provenance(
            source=RecordSource.FREEBLOCK,
            algorithm="test",
            page_number=page_number,
            file_offset=file_offset,
            version=version,
            confidence=0.85,
        ),
    )


def test_dedupe_keeps_same_content_at_different_offsets():
    first = _sample_record(page_number=2, file_offset=100)
    second = _sample_record(page_number=3, file_offset=200)
    result = _dedupe_records([first, second])
    assert len(result) == 2


def test_dedupe_collapses_identical_physical_duplicates():
    first = _sample_record(page_number=2, file_offset=100, version=0)
    second = _sample_record(page_number=2, file_offset=100, version=0)
    result = _dedupe_records([first, second])
    assert len(result) == 1


def test_dedupe_keeps_same_content_in_different_wal_versions():
    first = _sample_record(page_number=2, file_offset=100, version=1)
    second = _sample_record(page_number=2, file_offset=100, version=2)
    result = _dedupe_records([first, second])
    assert len(result) == 2


def test_dedupe_key_handles_blob_columns():
    blob_columns = {
        "payload": {
            "__type__": "blob",
            "encoding": "base64",
            "value": "AQID",
            "size": 3,
        }
    }
    first = _sample_record(page_number=1, file_offset=10, columns=blob_columns)
    second = _sample_record(page_number=2, file_offset=20, columns=blob_columns)
    result = _dedupe_records([first, second])
    assert len(result) == 2
