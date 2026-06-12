"""Rollback journal recovery tests."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from zeusdb.engine import AnalyzeOptions, ForensicEngine
from zeusdb.models import NormalizedRecord, Provenance, RecordSource
from zeusdb.output.tsv_export import export_tsv
from zeusdb.reader.database import close_artifacts, open_artifacts
from zeusdb.recover.engine import _signature_for_table, finalize_records, recover_journal_records


def _sample_record(
    *,
    page_number: int | None,
    file_offset: int | None,
    source: RecordSource,
    occurrence_id: str,
    row_id: int = 1,
) -> NormalizedRecord:
    provenance = Provenance(
        source=source,
        algorithm="test",
        page_number=page_number,
        file_offset=file_offset,
        version=-1 if source == RecordSource.JOURNAL else 0,
        confidence=0.9 if source == RecordSource.JOURNAL else 1.0,
        occurrence_id=occurrence_id,
    )
    return NormalizedRecord(
        table_name="users",
        row_id=row_id,
        columns={"name": "Alice"},
        is_live=source == RecordSource.LIVE,
        is_deleted=source != RecordSource.LIVE,
        provenances=[provenance],
    )


def _persist_journal_db(tmp_path: Path) -> Path:
    """Create a DELETE/PERSIST DB with a committed update (journal sidecar retained)."""
    db_path = tmp_path / "journalcase.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=PERSIST")
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.execute("UPDATE users SET name = 'AliceUpdated' WHERE id = 1")
    conn.commit()
    conn.close()
    return db_path


def test_recover_journal_records_returns_journal_provenance(tmp_path: Path):
    db_path = _persist_journal_db(tmp_path)
    bundle = open_artifacts(db_path)
    try:
        base_version = bundle.version_history.versions[0]
        entry = next(
            e for e in base_version.master_schema.master_schema_entries if e.name == "users"
        )
        signature = _signature_for_table(bundle, entry)
        assert signature is not None
        records = recover_journal_records(
            bundle,
            entry,
            signature,
            text_encoding=bundle.encoding,
            source_sha256=bundle.source_sha256,
        )
    finally:
        close_artifacts(bundle)

    assert records
    assert any(
        p.source == RecordSource.JOURNAL
        for record in records
        for p in record.provenances
    )


def test_recover_journal_records_empty_without_sidecar(sample_db):
    bundle = open_artifacts(sample_db)
    try:
        base_version = bundle.version_history.versions[0]
        entry = next(
            e for e in base_version.master_schema.master_schema_entries if e.name == "users"
        )
        signature = _signature_for_table(bundle, entry)
        assert signature is not None
        records = recover_journal_records(
            bundle,
            entry,
            signature,
            text_encoding=bundle.encoding,
            source_sha256=bundle.source_sha256,
        )
    finally:
        close_artifacts(bundle)

    assert records == []


def test_finalize_merges_journal_trace_with_live_row():
    """v1.1 semantics: live + journal provenances on same row_id → is_live wins."""
    live = _sample_record(
        page_number=1,
        file_offset=10,
        source=RecordSource.LIVE,
        occurrence_id="live-1",
    )
    journal = _sample_record(
        page_number=1,
        file_offset=512,
        source=RecordSource.JOURNAL,
        occurrence_id="journal-1",
    )
    finalized = finalize_records([live, journal], "hash123")
    assert len(finalized) == 1
    assert finalized[0].is_live is True
    assert finalized[0].is_deleted is False
    assert any(p.source == RecordSource.LIVE for p in finalized[0].provenances)
    assert any(p.source == RecordSource.JOURNAL for p in finalized[0].provenances)


def test_journal_ids_are_deterministic(tmp_path: Path):
    db_path = _persist_journal_db(tmp_path)
    first = ForensicEngine().analyze(db_path, AnalyzeOptions(carve=True))
    second = ForensicEngine().analyze(db_path, AnalyzeOptions(carve=True))
    journal_first = [
        r for r in first.records if any(p.source == RecordSource.JOURNAL for p in r.provenances)
    ]
    journal_second = [
        r for r in second.records if any(p.source == RecordSource.JOURNAL for p in r.provenances)
    ]
    assert journal_first
    assert {r.record_id for r in journal_first} == {r.record_id for r in journal_second}
    first_occ = {
        p.occurrence_id
        for r in journal_first
        for p in r.provenances
        if p.source == RecordSource.JOURNAL
    }
    second_occ = {
        p.occurrence_id
        for r in journal_second
        for p in r.provenances
        if p.source == RecordSource.JOURNAL
    }
    assert first_occ == second_occ


def test_journal_records_appear_in_tsv_export(tmp_path: Path):
    db_path = _persist_journal_db(tmp_path)
    result = ForensicEngine().analyze(db_path, AnalyzeOptions(carve=True))
    tsv_path = export_tsv(result, tmp_path / "journal.tsv")
    with tsv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    journal_rows = [row for row in rows if "journal@" in row["provenance_summary"]]
    assert journal_rows
    assert all(row["record_id"] for row in journal_rows)
