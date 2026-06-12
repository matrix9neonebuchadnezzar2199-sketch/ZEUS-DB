"""Output contract tests."""

import json
from pathlib import Path

from zeusdb.engine import AnalyzeOptions, ForensicEngine
from zeusdb.output.case_export import export_case
from zeusdb.output.json_export import export_json
from zeusdb.output.tsv_export import export_tsv


def test_json_export_schema(sample_db, tmp_path: Path):
    engine = ForensicEngine()
    result = engine.analyze(sample_db, AnalyzeOptions(carve=True))
    out = export_json(result, tmp_path / "out.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.1"
    assert "records" in payload
    assert "summary" in payload


def test_tsv_and_case_export(sample_db, tmp_path: Path):
    engine = ForensicEngine()
    result = engine.analyze(sample_db)
    tsv = export_tsv(result, tmp_path / "out.tsv")
    case = export_case(result, tmp_path / "case.json")
    assert tsv.exists()
    assert case.exists()
