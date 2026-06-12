"""Reader layer tests."""

from zeusdb.reader.database import list_table_names, open_artifacts


def test_open_and_list_tables(sample_db):
    bundle = open_artifacts(sample_db)
    tables = list_table_names(bundle)
    assert "users" in tables
    assert bundle.page_size >= 512


def test_live_row_count(sample_db):
    from zeusdb.recover.engine import recover_live_records

    bundle = open_artifacts(sample_db)
    records = recover_live_records(bundle)
    assert len(records) == 2
    assert all(r.is_live for r in records)
