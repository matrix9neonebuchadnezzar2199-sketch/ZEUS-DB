"""Dedupe and aggregation behavior tests."""

from __future__ import annotations

from zeusdb.identity import record_id as derive_record_id
from zeusdb.models import NormalizedRecord, Provenance, RecordSource
from zeusdb.recover.engine import (
    _aggregate_records,
    aggregate_record_confidence,
    finalize_records,
)


def _sample_record(
    *,
    page_number: int | None,
    file_offset: int | None,
    version: int | None = 0,
    row_id: int = 1,
    columns: dict | None = None,
    source: RecordSource = RecordSource.FREEBLOCK,
    confidence: float = 0.85,
    occurrence_id: str | None = None,
) -> NormalizedRecord:
    provenance = Provenance(
        source=source,
        algorithm="test",
        page_number=page_number,
        file_offset=file_offset,
        version=version,
        confidence=confidence,
        occurrence_id=occurrence_id or f"occ-{page_number}-{file_offset}",
    )
    return NormalizedRecord(
        table_name="users",
        row_id=row_id,
        columns=columns or {"name": "Alice"},
        is_live=source == RecordSource.LIVE,
        is_deleted=source != RecordSource.LIVE,
        provenances=[provenance],
    )


def test_aggregate_merges_same_logical_record_at_different_offsets():
    first = _sample_record(page_number=2, file_offset=100, occurrence_id="a")
    second = _sample_record(page_number=3, file_offset=200, occurrence_id="b")
    result = _aggregate_records([first, second])
    assert len(result) == 1
    assert len(result[0].provenances) == 2


def test_aggregate_collapses_duplicate_occurrence_ids():
    first = _sample_record(page_number=2, file_offset=100, occurrence_id="same")
    second = _sample_record(page_number=2, file_offset=100, occurrence_id="same")
    result = _aggregate_records([first, second])
    assert len(result) == 1
    assert len(result[0].provenances) == 1


def test_aggregate_separates_row_id_less_records_by_fingerprint():
    salvage_a = NormalizedRecord(
        table_name="__salvage__",
        columns={"page_number": 1},
        is_deleted=True,
        provenances=[
            Provenance(
                source=RecordSource.SALVAGE,
                algorithm="test",
                occurrence_id="s1",
            )
        ],
    )
    salvage_b = NormalizedRecord(
        table_name="__salvage__",
        columns={"page_number": 2},
        is_deleted=True,
        provenances=[
            Provenance(
                source=RecordSource.SALVAGE,
                algorithm="test",
                occurrence_id="s2",
            )
        ],
    )
    result = _aggregate_records([salvage_a, salvage_b])
    assert len(result) == 2


def test_confidence_live_provenance_wins():
    live = Provenance(source=RecordSource.LIVE, algorithm="live", confidence=1.0)
    deleted = Provenance(source=RecordSource.FREEBLOCK, algorithm="fb", confidence=0.85)
    assert aggregate_record_confidence([deleted, live]) == 1.0


def test_confidence_max_without_live():
    first = Provenance(source=RecordSource.FREEBLOCK, algorithm="fb", confidence=0.85)
    second = Provenance(source=RecordSource.UNALLOCATED, algorithm="ua", confidence=0.8)
    assert aggregate_record_confidence([first, second]) == 0.85


def test_record_id_is_deterministic():
    columns = {"name": "Alice"}
    first = derive_record_id(
        source_sha256="abc",
        table_name="users",
        row_id=1,
        columns=columns,
    )
    second = derive_record_id(
        source_sha256="abc",
        table_name="users",
        row_id=1,
        columns=columns,
    )
    assert first == second


def test_finalize_records_assigns_record_id_and_confidence():
    record = _sample_record(page_number=1, file_offset=10, source=RecordSource.FREEBLOCK)
    finalized = finalize_records([record], "hash123")
    assert len(finalized) == 1
    assert finalized[0].record_id
    assert finalized[0].confidence == 0.85
    assert finalized[0].is_live is False
    assert finalized[0].is_deleted is True


def test_finalize_live_with_deletion_trace_is_not_deleted():
    live = _sample_record(
        page_number=1,
        file_offset=10,
        source=RecordSource.LIVE,
        occurrence_id="live-1",
    )
    trace = _sample_record(
        page_number=2,
        file_offset=200,
        source=RecordSource.FREEBLOCK,
        occurrence_id="fb-1",
    )
    finalized = finalize_records([live, trace], "hash123")
    assert len(finalized) == 1
    assert len(finalized[0].provenances) == 2
    assert finalized[0].is_live is True
    assert finalized[0].is_deleted is False
    assert finalized[0].confidence == 1.0
