"""Read-only SQLite artifact loading via sqlite-dissect."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlite_dissect.constants import ROLLBACK_JOURNAL_POSTFIX, WAL_FILE_POSTFIX
from sqlite_dissect.file.database.database import Database
from sqlite_dissect.file.journal.jounal import RollbackJournal
from sqlite_dissect.file.wal.wal import WriteAheadLog
from sqlite_dissect.version_history import VersionHistory


@dataclass(slots=True)
class ArtifactBundle:
    """Opened database with optional WAL and rollback journal."""

    database_path: Path
    database: Database
    wal_path: Path | None
    write_ahead_log: WriteAheadLog | None
    journal_path: Path | None
    rollback_journal: RollbackJournal | None
    version_history: VersionHistory

    @property
    def page_size(self) -> int:
        """Return database page size from header."""
        return int(self.database.database_header.page_size)

    @property
    def encoding(self) -> str:
        """Return database text encoding label."""
        return str(self.database.database_text_encoding or "UTF-8")


def resolve_sidecar_paths(database_path: Path) -> tuple[Path | None, Path | None]:
    """Locate WAL and rollback journal sidecars if present."""
    wal_path = database_path.with_name(database_path.name + WAL_FILE_POSTFIX)
    journal_path = database_path.with_name(database_path.name + ROLLBACK_JOURNAL_POSTFIX)
    wal = wal_path if wal_path.exists() and wal_path.stat().st_size > 0 else None
    journal = journal_path if journal_path.exists() and journal_path.stat().st_size > 0 else None
    return wal, journal


def open_artifacts(
    database_path: str | Path,
    *,
    wal_path: str | Path | None = None,
    journal_path: str | Path | None = None,
    strict_format_checking: bool = True,
) -> ArtifactBundle:
    """Open database and associated journal files read-only.

    Args:
        database_path: Path to the main SQLite database file.
        wal_path: Optional explicit WAL path override.
        journal_path: Optional explicit rollback journal path override.
        strict_format_checking: When True, enforce sqlite-dissect format checks.

    Returns:
        Bundle of parsed artifacts ready for version/recovery layers.

    Raises:
        FileNotFoundError: If the database file does not exist.
        ValueError: If both WAL and rollback journal are present.
    """
    db_path = Path(database_path).resolve()
    if not db_path.exists():
        msg = f"Database not found: {db_path}"
        raise FileNotFoundError(msg)

    resolved_wal = Path(wal_path).resolve() if wal_path else None
    resolved_journal = Path(journal_path).resolve() if journal_path else None
    if resolved_wal is None or resolved_journal is None:
        sidecar_wal, sidecar_journal = resolve_sidecar_paths(db_path)
        resolved_wal = resolved_wal or sidecar_wal
        resolved_journal = resolved_journal or sidecar_journal

    if resolved_wal and resolved_journal:
        msg = "Both WAL and rollback journal found; only one journal mode is valid."
        raise ValueError(msg)

    database = Database(str(db_path), strict_format_checking=strict_format_checking)
    write_ahead_log = (
        WriteAheadLog(str(resolved_wal), strict_format_checking=strict_format_checking)
        if resolved_wal
        else None
    )
    rollback_journal = RollbackJournal(str(resolved_journal)) if resolved_journal else None
    version_history = VersionHistory(database, write_ahead_log)

    return ArtifactBundle(
        database_path=db_path,
        database=database,
        wal_path=resolved_wal,
        write_ahead_log=write_ahead_log,
        journal_path=resolved_journal,
        rollback_journal=rollback_journal,
        version_history=version_history,
    )


def close_artifacts(bundle: ArtifactBundle) -> None:
    """Close read-only file handles opened by sqlite-dissect."""
    bundle.database.file_handle.close()
    if bundle.write_ahead_log is not None:
        bundle.write_ahead_log.file_handle.close()
    if bundle.rollback_journal is not None:
        bundle.rollback_journal.file_handle.close()


def list_table_names(bundle: ArtifactBundle) -> list[str]:
    """Return user table names from master schema."""
    from sqlite_dissect.constants import MASTER_SCHEMA_ROW_TYPE

    return [
        entry.name
        for entry in bundle.database.master_schema.master_schema_entries
        if entry.row_type == MASTER_SCHEMA_ROW_TYPE.TABLE
        and not entry.internal_schema_object
    ]
