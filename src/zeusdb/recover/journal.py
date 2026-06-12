"""Rollback journal record recovery via sqlite-dissect RollBackJournalCarver."""

from __future__ import annotations

from typing import Any

from sqlite_dissect.carving.rollback_journal_carver import RollBackJournalCarver
from sqlite_dissect.constants import BASE_VERSION_NUMBER

from zeusdb.models import NormalizedRecord, RecordSource
from zeusdb.reader.database import ArtifactBundle
from zeusdb.recover.convert import cell_to_record

# WAL version-carve と同じ暫定値（journal は before-image のため 0.9）
_JOURNAL_CARVE_CONFIDENCE = 0.9


def recover_journal_records(
    bundle: ArtifactBundle,
    master_schema_entry: Any,
    signature: Any,
    *,
    text_encoding: str,
    source_sha256: str,
) -> list[NormalizedRecord]:
    """Carve deleted records from a rollback journal sidecar.

    Provenance semantics (sqlite-dissect vendor behavior):

    - ``page_number``: the **database page number** stored in the journal page
      record header (which DB page the before-image belongs to).
    - ``file_offset``: byte offset within the **rollback journal file**, not the
      main ``.db`` file. ``RollBackJournalCarver`` passes
      ``offset + page_record_header_size`` as ``page_offset`` into
      ``SignatureCarver.carve_unallocated_space``, and carved cells compute
      ``file_offset`` relative to that journal-local base.
    - ``occurrence_id`` still uses ``source_sha256`` of the **database file**
      (consistent with WAL carve and v1.1 ID policy).

    Args:
        bundle: Open artifact bundle with optional rollback journal.
        master_schema_entry: sqlite-dissect master schema table entry.
        signature: Table carving signature from ``create_table_signature``.
        text_encoding: Database text encoding label.
        source_sha256: SHA-256 of the main database file.

    Returns:
        Normalized records with ``source=JOURNAL`` provenance entries.
    """
    if bundle.rollback_journal is None:
        return []

    base_version = bundle.version_history.versions[BASE_VERSION_NUMBER]
    carved_commits = RollBackJournalCarver.carve(
        bundle.rollback_journal,
        base_version,
        master_schema_entry,
        signature,
    )

    records: list[NormalizedRecord] = []
    for commit in carved_commits:
        version_number = getattr(commit, "version_number", -1)
        for cell in commit.carved_cells.values():
            records.append(
                cell_to_record(
                    cell,
                    master_schema_entry,
                    source=RecordSource.JOURNAL,
                    algorithm="sqlite-dissect-journal-carve",
                    is_live=False,
                    is_deleted=True,
                    text_encoding=text_encoding,
                    source_sha256=source_sha256,
                    version=version_number,
                    confidence=_JOURNAL_CARVE_CONFIDENCE,
                )
            )
    return records
