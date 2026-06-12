"""Version timeline tests."""

from zeusdb.engine import AnalyzeOptions, ForensicEngine
from zeusdb.reader.database import open_artifacts
from zeusdb.version.timeline import build_timeline


def test_timeline_base_version(sample_db):
    engine = ForensicEngine()
    result = engine.analyze(sample_db)
    assert result.timeline[0].label == "base_database"
    assert result.timeline[0].version == 0


def test_wal_sidecar_detected(wal_db):
    db_path, wal_path = wal_db
    bundle = open_artifacts(db_path)
    try:
        if wal_path.exists():
            assert bundle.wal_path is not None
        timeline = build_timeline(bundle)
        assert timeline[0].version == 0
    finally:
        from zeusdb.reader.database import close_artifacts

        close_artifacts(bundle)
