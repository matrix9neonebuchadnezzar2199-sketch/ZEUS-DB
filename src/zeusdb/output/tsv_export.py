"""TSV export for spreadsheet review."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from zeusdb.models import AnalysisResult
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


def export_tsv(result: AnalysisResult, output_path: str | Path) -> Path:
    """Write all records to a tab-separated values file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "table_name",
        "row_id",
        "is_live",
        "is_deleted",
        "source",
        "algorithm",
        "page_number",
        "file_offset",
        "version",
        "confidence",
        "columns_json",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for record in result.records:
            writer.writerow(
                {
                    "table_name": record.table_name,
                    "row_id": record.row_id,
                    "is_live": record.is_live,
                    "is_deleted": record.is_deleted,
                    "source": record.provenance.source.value,
                    "algorithm": record.provenance.algorithm,
                    "page_number": record.provenance.page_number,
                    "file_offset": record.provenance.file_offset,
                    "version": record.provenance.version,
                    "confidence": record.provenance.confidence,
                    "columns_json": serialize_columns_for_tsv(record.columns),
                }
            )
    return path
