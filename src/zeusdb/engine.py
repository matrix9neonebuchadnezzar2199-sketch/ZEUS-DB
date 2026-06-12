"""Main forensic analysis orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zeusdb.models import AnalysisResult
from zeusdb.reader.database import ArtifactBundle, close_artifacts, list_table_names, open_artifacts
from zeusdb.recover.engine import recover_deleted_records, recover_live_records
from zeusdb.salvage.raw_carver import salvage_raw_pages
from zeusdb.version.timeline import build_timeline


@dataclass(slots=True)
class AnalyzeOptions:
    """Runtime options for a forensic analysis run."""

    carve: bool = True
    carve_freelist: bool = True
    boyer_moore: bool = True
    salvage: bool = False
    tables: list[str] | None = None
    strict_format_checking: bool = True
    wal_path: str | None = None
    journal_path: str | None = None


class ForensicEngine:
    """Unified SQLite forensic engine."""

    def analyze(
        self,
        database_path: str | Path,
        options: AnalyzeOptions | None = None,
    ) -> AnalysisResult:
        """Run full read-only analysis on a SQLite artifact set.

        Args:
            database_path: Path to main `.db` / `.sqlite` file.
            options: Carving and export behavior flags.

        Returns:
            Normalized analysis result with timeline and provenance records.
        """
        opts = options or AnalyzeOptions()
        bundle = open_artifacts(
            database_path,
            wal_path=opts.wal_path,
            journal_path=opts.journal_path,
            strict_format_checking=opts.strict_format_checking,
        )
        try:
            return self.analyze_bundle(bundle, opts)
        finally:
            close_artifacts(bundle)

    def analyze_bundle(
        self,
        bundle: ArtifactBundle,
        options: AnalyzeOptions | None = None,
    ) -> AnalysisResult:
        """Analyze an already-open artifact bundle."""
        opts = options or AnalyzeOptions()
        tables = opts.tables or list_table_names(bundle)
        timeline = build_timeline(bundle)

        records = recover_live_records(bundle, tables)
        if opts.carve:
            records.extend(
                recover_deleted_records(
                    bundle,
                    table_names=tables,
                    carve_freelist=opts.carve_freelist,
                    boyer_moore=opts.boyer_moore,
                )
            )
        if opts.salvage:
            records.extend(salvage_raw_pages(bundle.database_path))

        return AnalysisResult(
            database_path=str(bundle.database_path),
            wal_path=str(bundle.wal_path) if bundle.wal_path else None,
            journal_path=str(bundle.journal_path) if bundle.journal_path else None,
            page_size=bundle.page_size,
            encoding=bundle.encoding,
            tables=tables,
            timeline=timeline,
            records=records,
            metadata={
                "carve_enabled": opts.carve,
                "carve_freelist": opts.carve_freelist,
                "boyer_moore": opts.boyer_moore,
                "salvage_enabled": opts.salvage,
                "engine": "ZEUS-DB",
                "core": "sqlite-dissect",
            },
        )
