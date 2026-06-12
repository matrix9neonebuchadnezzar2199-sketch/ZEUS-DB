"""Engine integration tests."""

from zeusdb.engine import AnalyzeOptions, ForensicEngine
from zeusdb.reader.database import close_artifacts, open_artifacts


def test_engine_metadata(sample_db):
    engine = ForensicEngine()
    result = engine.analyze(sample_db)
    assert result.metadata["engine"] == "ZEUS-DB"
    assert result.metadata["source_sha256"]
    assert "users" in result.tables
    assert result.to_dict()["schema_version"] == "1.1"
    assert result.records[0].record_id
    assert result.records[0].provenances


def test_analyze_bundle_finalizes_all_record_sources(sample_db):
    engine = ForensicEngine()
    bundle = open_artifacts(sample_db)
    try:
        result = engine.analyze_bundle(
            bundle,
            AnalyzeOptions(carve=True, salvage=True),
        )
    finally:
        close_artifacts(bundle)

    assert all(record.record_id for record in result.records)
    assert all(record.provenances for record in result.records)
    live_rows = [record for record in result.records if record.table_name == "users" and record.is_live]
    assert live_rows
    assert all(record.is_deleted is False for record in live_rows)


def test_salvage_mode(sample_db):
    engine = ForensicEngine()
    result = engine.analyze(sample_db, AnalyzeOptions(carve=False, salvage=True))
    salvage_rows = [r for r in result.records if r.table_name == "__salvage__"]
    assert len(salvage_rows) >= 1
