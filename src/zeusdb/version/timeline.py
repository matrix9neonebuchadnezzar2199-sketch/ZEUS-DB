"""WAL/journal version timeline built on sqlite-dissect VersionHistory."""

from __future__ import annotations

from sqlite_dissect.constants import BASE_VERSION_NUMBER, MASTER_SCHEMA_ROW_TYPE

from zeusdb.models import TimelineEntry
from zeusdb.reader.database import ArtifactBundle


def build_timeline(bundle: ArtifactBundle) -> list[TimelineEntry]:
    """Build commit-version timeline from database + WAL frames.

    Args:
        bundle: Open artifact bundle with version history.

    Returns:
        Ordered timeline entries from base DB through WAL commits.
    """
    entries: list[TimelineEntry] = [
        TimelineEntry(
            version=BASE_VERSION_NUMBER,
            label="base_database",
            source_file=str(bundle.database_path),
        )
    ]

    if bundle.write_ahead_log is not None:
        for version_number in sorted(bundle.version_history.versions.keys()):
            if version_number == BASE_VERSION_NUMBER:
                continue
            version = bundle.version_history.versions[version_number]
            commit_number = version_number - BASE_VERSION_NUMBER
            entries.append(
                TimelineEntry(
                    version=version_number,
                    label=f"wal_commit_{commit_number}",
                    source_file=str(bundle.wal_path or bundle.database_path),
                    commit_record_number=commit_number,
                )
            )

    if bundle.rollback_journal is not None:
        entries.append(
            TimelineEntry(
                version=-1,
                label="rollback_journal_present",
                source_file=str(bundle.journal_path or bundle.database_path),
            )
        )

    return entries


def tables_in_version(bundle: ArtifactBundle, version_number: int) -> list[str]:
    """List table names available in a specific version snapshot."""
    version = bundle.version_history.versions.get(version_number)
    if version is None:
        return []
    return [
        entry.name
        for entry in version.master_schema.master_schema_entries
        if entry.row_type == MASTER_SCHEMA_ROW_TYPE.TABLE
        and not entry.internal_schema_object
    ]
