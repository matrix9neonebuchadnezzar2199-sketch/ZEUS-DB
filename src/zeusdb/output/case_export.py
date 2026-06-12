"""CASE 1.1 export wrapper."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zeusdb.models import AnalysisResult


def export_case(result: AnalysisResult, output_path: str | Path) -> Path:
    """Write a minimal CASE-compatible JSON bundle."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "@context": "https://caseontology.org/context/case-1.1.0.jsonld",
        "@type": "case:Case",
        "case:description": "ZEUS-DB SQLite forensic analysis",
        "case:created": datetime.now(timezone.utc).isoformat(),
        "zeusdb:analysis": result.to_dict(),
        "zeusdb:tool": {
            "name": "ZEUS-DB",
            "version": "0.1.0",
            "engine": "sqlite-dissect-core",
        },
        "zeusdb:source_sha256": result.metadata.get("source_sha256"),
    }

    import json

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
