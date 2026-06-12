"""Dropped table artifact recovery from raw page slack."""

from __future__ import annotations

import re
from pathlib import Path

from zeusdb.models import NormalizedRecord, Provenance, RecordSource

_CREATE_TABLE_RE = re.compile(
    rb"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?\s*\(",
    re.IGNORECASE,
)


def recover_dropped_table_artifacts(
    database_path: str | Path,
    page_size: int,
) -> list[NormalizedRecord]:
    """Scan database pages for CREATE TABLE SQL remnants (dropped table hints)."""
    records: list[NormalizedRecord] = []
    raw = Path(database_path).read_bytes()
    for page_index in range(len(raw) // page_size):
        page_offset = page_index * page_size
        page_data = raw[page_offset : page_offset + page_size]
        for match in _CREATE_TABLE_RE.finditer(page_data):
            table_name = match.group(1).decode("utf-8", errors="replace")
            records.append(
                NormalizedRecord(
                    table_name=table_name,
                    columns={"sql_fragment": match.group(0).decode("utf-8", errors="replace")},
                    is_live=False,
                    is_deleted=True,
                    provenance=Provenance(
                        source=RecordSource.DROPPED_TABLE,
                        algorithm="fqlite-dropped-table-scan",
                        page_number=page_index + 1,
                        file_offset=page_offset + match.start(),
                        confidence=0.6,
                        notes="CREATE TABLE fragment found outside live schema",
                    ),
                )
            )
    return records
