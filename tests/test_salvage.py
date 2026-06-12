"""Salvage layer tests."""

from zeusdb.identity import file_sha256
from zeusdb.salvage.raw_carver import salvage_raw_pages


def test_salvage_non_empty_pages(sample_db):
    records = salvage_raw_pages(sample_db, source_sha256=file_sha256(sample_db))
    assert len(records) >= 1
    assert records[0].provenances[0].algorithm == "undark-sqbrite-raw-page-scan"
    assert records[0].provenances[0].occurrence_id is not None
