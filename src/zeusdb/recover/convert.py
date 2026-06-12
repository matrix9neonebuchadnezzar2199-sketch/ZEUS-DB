"""Convert sqlite-dissect cells into normalized records."""

from __future__ import annotations

import base64
from typing import Any

from zeusdb.identity import occurrence_id as derive_occurrence_id
from zeusdb.models import NormalizedRecord, Provenance, RecordSource

_BLOB_TYPE = "blob"
_UNKNOWN_SERIAL_REPLACEMENT_THRESHOLD = 0.1


def normalize_sqlite_encoding(encoding_label: str) -> str:
    """Map sqlite-dissect encoding labels to Python codec names.

    Args:
        encoding_label: Value from ``ArtifactBundle.encoding`` (e.g. ``UTF-16le``).

    Returns:
        Python codec name. Unknown labels fall back to ``utf-8``.
    """
    normalized = encoding_label.strip().lower().replace("_", "-")
    mapping = {
        "utf-8": "utf-8",
        "utf-16le": "utf-16-le",
        "utf-16-le": "utf-16-le",
        "utf-16be": "utf-16-be",
        "utf-16-be": "utf-16-be",
    }
    return mapping.get(normalized, "utf-8")


def _blob_column_value(raw: bytes) -> dict[str, Any]:
    """Wrap raw bytes in a reversible JSON-friendly BLOB structure."""
    return {
        "__type__": _BLOB_TYPE,
        "encoding": "base64",
        "value": base64.b64encode(raw).decode("ascii"),
        "size": len(raw),
    }


def is_blob_column(value: Any) -> bool:
    """Return True when a column value is a normalized BLOB wrapper."""
    return isinstance(value, dict) and value.get("__type__") == _BLOB_TYPE


def _decode_text_bytes(value: bytes, text_encoding: str) -> str:
    """Decode TEXT payload bytes using the database header encoding."""
    codec = normalize_sqlite_encoding(text_encoding)
    return value.decode(codec, errors="replace")


def _decode_bytes_without_serial_type(value: bytes, text_encoding: str) -> Any:
    """Decode carved bytes when serial type metadata is unavailable.

    Attempts TEXT decoding with ``errors=\"replace\"`` first. If replacement
    characters exceed ``_UNKNOWN_SERIAL_REPLACEMENT_THRESHOLD`` of the decoded
    length, the payload is preserved as a BLOB wrapper instead.
    """
    decoded = _decode_text_bytes(value, text_encoding)
    if not decoded:
        return decoded
    replacement_ratio = decoded.count("\ufffd") / len(decoded)
    if replacement_ratio > _UNKNOWN_SERIAL_REPLACEMENT_THRESHOLD:
        return _blob_column_value(value)
    return decoded


def _column_value(
    value: Any,
    serial_type: int | None,
    text_encoding: str,
) -> Any:
    """Convert one record column value with SQLite serial-type awareness."""
    if not isinstance(value, bytes):
        return value

    if serial_type is not None:
        if serial_type >= 12 and serial_type % 2 == 0:
            return _blob_column_value(value)
        if serial_type >= 13 and serial_type % 2 == 1:
            return _decode_text_bytes(value, text_encoding)

    return _decode_bytes_without_serial_type(value, text_encoding)


def _column_map(
    cell: Any,
    master_schema_entry: Any,
    *,
    text_encoding: str,
) -> dict[str, Any]:
    """Map record column indices to schema column names with type-aware decoding."""
    columns: dict[str, Any] = {}
    definitions = {
        col.index: col.column_name for col in master_schema_entry.column_definitions
    }
    payload = getattr(cell, "payload", None)
    if payload is None:
        return columns
    for record_column in payload.record_columns:
        name = definitions.get(record_column.index, f"col_{record_column.index}")
        serial_type = getattr(record_column, "serial_type", None)
        columns[name] = _column_value(
            record_column.value,
            serial_type,
            text_encoding,
        )
    return columns


def cell_to_record(
    cell: Any,
    master_schema_entry: Any,
    *,
    source: RecordSource,
    algorithm: str,
    is_live: bool,
    is_deleted: bool,
    source_sha256: str,
    text_encoding: str = "UTF-8",
    version: int | None = None,
    confidence: float = 1.0,
) -> NormalizedRecord:
    """Convert a sqlite-dissect cell into a NormalizedRecord."""
    page_number = getattr(cell, "page_number", None)
    file_offset = getattr(cell, "file_offset", None)
    location = getattr(getattr(cell, "location", None), "name", None)
    row_id = getattr(cell, "row_id", None)

    provenance = Provenance(
        source=source,
        algorithm=algorithm,
        page_number=page_number,
        file_offset=file_offset,
        version=version,
        confidence=confidence,
        cell_location=location,
        occurrence_id=derive_occurrence_id(
            source_sha256=source_sha256,
            source=source.value,
            page_number=page_number,
            file_offset=file_offset,
            version=version,
            row_id=row_id,
        ),
    )

    return NormalizedRecord(
        table_name=master_schema_entry.name,
        row_id=row_id,
        columns=_column_map(cell, master_schema_entry, text_encoding=text_encoding),
        is_live=is_live,
        is_deleted=is_deleted,
        provenance=provenance,
    )
