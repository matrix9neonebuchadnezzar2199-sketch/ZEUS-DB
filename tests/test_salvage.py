"""Salvage layer tests."""

from zeusdb.salvage.raw_carver import salvage_raw_pages


def test_salvage_non_empty_pages(sample_db):
    records = salvage_raw_pages(sample_db)
    assert len(records) >= 1
    assert records[0].provenance.algorithm == "undark-sqbrite-raw-page-scan"
