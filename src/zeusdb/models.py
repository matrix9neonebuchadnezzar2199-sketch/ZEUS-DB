"""Shared data models for normalized forensic output."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class RecordSource(StrEnum):
    """Physical origin of a recovered row."""

    LIVE = "live"
    FREEBLOCK = "freeblock"
    UNALLOCATED = "unallocated"
    FREELIST = "freelist"
    WAL = "wal"
    JOURNAL = "journal"
    CARVED = "carved"
    DROPPED_TABLE = "dropped_table"
    SALVAGE = "salvage"


@dataclass(slots=True)
class Provenance:
    """Evidence chain metadata for a recovered record."""

    source: RecordSource
    algorithm: str
    page_number: int | None = None
    file_offset: int | None = None
    version: int | None = None
    confidence: float = 1.0
    cell_location: str | None = None
    notes: str | None = None
    occurrence_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize provenance for JSON export."""
        data = asdict(self)
        data["source"] = self.source.value
        return data


@dataclass(slots=True)
class NormalizedRecord:
    """Unified row representation across all recovery algorithms."""

    table_name: str
    columns: dict[str, Any]
    row_id: int | None = None
    is_live: bool = False
    is_deleted: bool = False
    provenance: Provenance = field(
        default_factory=lambda: Provenance(source=RecordSource.LIVE, algorithm="unknown")
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize record for JSON export."""
        return {
            "table_name": self.table_name,
            "row_id": self.row_id,
            "columns": self.columns,
            "is_live": self.is_live,
            "is_deleted": self.is_deleted,
            "provenance": self.provenance.to_dict(),
        }


@dataclass(slots=True)
class TimelineEntry:
    """One version/commit in the database timeline."""

    version: int
    label: str
    source_file: str
    tables_with_changes: list[str] = field(default_factory=list)
    commit_record_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize timeline entry."""
        return asdict(self)


@dataclass(slots=True)
class AnalysisResult:
    """Complete analysis output contract for CLI, HTTP, and AISSS."""

    database_path: str
    page_size: int
    encoding: str
    tables: list[str]
    timeline: list[TimelineEntry]
    records: list[NormalizedRecord]
    wal_path: str | None = None
    journal_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize full analysis result."""
        return {
            "schema_version": "1.0",
            "database_path": self.database_path,
            "wal_path": self.wal_path,
            "journal_path": self.journal_path,
            "page_size": self.page_size,
            "encoding": self.encoding,
            "tables": self.tables,
            "timeline": [entry.to_dict() for entry in self.timeline],
            "records": [record.to_dict() for record in self.records],
            "metadata": self.metadata,
            "summary": {
                "total_records": len(self.records),
                "live_records": sum(1 for r in self.records if r.is_live),
                "deleted_records": sum(1 for r in self.records if r.is_deleted),
            },
        }
