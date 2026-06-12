"""JSON export for AISSS integration contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zeusdb.models import AnalysisResult


def export_json(result: AnalysisResult, output_path: str | Path) -> Path:
    """Write analysis result as versioned JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def result_to_json_string(result: AnalysisResult) -> str:
    """Serialize analysis result to JSON string."""
    return json.dumps(result.to_dict(), ensure_ascii=False)
