"""Recovery layer tests."""

from zeusdb.engine import AnalyzeOptions, ForensicEngine


def test_carve_finds_deleted_or_live(sample_db):
    engine = ForensicEngine()
    result = engine.analyze(sample_db, AnalyzeOptions(carve=True))
    assert result.to_dict()["summary"]["live_records"] >= 2
    assert len(result.records) >= 2


def test_carver_boyer_moore_module(sample_db):
    from zeusdb.reader.database import open_artifacts
    from zeusdb.recover.carver import boyer_moore_search

    bundle = open_artifacts(sample_db)
    raw = bundle.database_path.read_bytes()
    matches = boyer_moore_search(raw, b"Bob")
    assert isinstance(matches, list)
