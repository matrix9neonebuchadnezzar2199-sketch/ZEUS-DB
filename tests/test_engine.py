"""Engine integration tests."""

from zeusdb.engine import AnalyzeOptions, ForensicEngine


def test_engine_metadata(sample_db):
    engine = ForensicEngine()
    result = engine.analyze(sample_db)
    assert result.metadata["engine"] == "ZEUS-DB"
    assert "users" in result.tables


def test_salvage_mode(sample_db):
    engine = ForensicEngine()
    result = engine.analyze(sample_db, AnalyzeOptions(carve=False, salvage=True))
    salvage_rows = [r for r in result.records if r.table_name == "__salvage__"]
    assert len(salvage_rows) >= 1
