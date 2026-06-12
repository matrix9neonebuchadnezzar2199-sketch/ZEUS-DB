"""Convert sqlite-dissect cells into normalized records."""

from __future__ import annotations

from typing import Any

from zeusdb.models import NormalizedRecord, Provenance, RecordSource


def _column_map(cell: Any, master_schema_entry: Any) -> dict[str, Any]:
    """Map record column indices to schema column names."""
    columns: dict[str, Any] = {}
    definitions = {
        col.index: col.column_name for col in master_schema_entry.column_definitions
    }
    payload = getattr(cell, "payload", None)
    if payload is None:
        return columns
    for record_column in payload.record_columns:
        name = definitions.get(record_column.index, f"col_{record_column.index}")
        value = record_column.value
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        columns[name] = value
    return columns


def cell_to_record(
    cell: Any,
    master_schema_entry: Any,
    *,
    source: RecordSource,
    algorithm: str,
    is_live: bool,
    is_deleted: bool,
    version: int | None = None,
    confidence: float = 1.0,
) -> NormalizedRecord:
    """Convert a sqlite-dissect cell into a NormalizedRecord."""
    page_number = getattr(cell, "page_number", None)
    file_offset = getattr(cell, "file_offset", None)
    location = getattr(getattr(cell, "location", None), "name", None)
    row_id = getattr(cell, "row_id", None)

    return NormalizedRecord(
        table_name=master_schema_entry.name,
        row_id=row_id,
        columns=_column_map(cell, master_schema_entry),
        is_live=is_live,
        is_deleted=is_deleted,
        provenance=Provenance(
            source=source,
            algorithm=algorithm,
            page_number=page_number,
            file_offset=file_offset,
            version=version,
            confidence=confidence,
            cell_location=location,
        ),
    )
