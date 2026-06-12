"""TSV export for spreadsheet review."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from zeusdb.models import AnalysisResult, Provenance
from zeusdb.recover.convert import is_blob_column


def flatten_column_value(value: Any) -> Any:
    """Flatten structured column values for tabular export."""
    if is_blob_column(value):
        return f"base64:{value['value']}"
    return value


def serialize_columns_for_tsv(columns: dict[str, Any]) -> str:
    """Serialize record columns with BLOB cells flattened for TSV."""
    flattened = {key: flatten_column_value(val) for key, val in columns.items()}
    return json.dumps(flattened, ensure_ascii=False, sort_keys=True)


def summarize_provenances(provenances: list[Provenance]) -> str:
    """Flatten multiple provenances into one TSV cell (1 record = 1 row).

    Format: ``source@offset`` joined by ``;`` (example: ``live;freeblock@4096``).
    """
    parts: list[str] = []
    for provenance in provenances:
        if provenance.file_offset is not None:
            parts.append(f"{provenance.source.value}@{provenance.file_offset}")
        else:
            parts.append(provenance.source.value)
    return ";".join(parts)


def export_tsv(result: AnalysisResult, output_path: str | Path) -> Path:
    """Write all records to a tab-separated values file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "record_id",
        "table_name",
        "row_id",
        "confidence",
        "is_live",
        "is_deleted",
        "provenance_summary",
        "columns_json",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for record in result.records:
            writer.writerow(
                {
                    "record_id": record.record_id,
                    "table_name": record.table_name,
                    "row_id": record.row_id,
                    "confidence": record.confidence,
                    "is_live": record.is_live,
                    "is_deleted": record.is_deleted,
                    "provenance_summary": summarize_provenances(record.provenances),
                    "columns_json": serialize_columns_for_tsv(record.columns),
                }
            )
    return path
