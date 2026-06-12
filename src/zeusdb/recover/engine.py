"""Recovery orchestration across all algorithms."""

from __future__ import annotations

from typing import Any

from sqlite_dissect.carving.signature import Signature
from sqlite_dissect.constants import BASE_VERSION_NUMBER, MASTER_SCHEMA_ROW_TYPE
from sqlite_dissect.file.database.utilities import aggregate_leaf_cells
from sqlite_dissect.file.schema.master import OrdinaryTableRow
from sqlite_dissect.interface import create_table_signature
from sqlite_dissect.version_history import VersionHistoryParser

from zeusdb.identity import aggregate_key, record_id as derive_record_id
from zeusdb.models import NormalizedRecord, Provenance, RecordSource
from zeusdb.reader.database import ArtifactBundle
from zeusdb.recover.carver import carve_pages_boyer_moore
from zeusdb.recover.convert import cell_to_record
from zeusdb.recover.dropped_table import recover_dropped_table_artifacts
from zeusdb.recover.freeblock import recover_freeblocks
from zeusdb.recover.freelist import recover_freelist_pages
from zeusdb.recover.journal import recover_journal_records
from zeusdb.recover.unallocated import recover_unallocated


def _signature_for_table(
    bundle: ArtifactBundle,
    master_schema_entry: Any,
) -> Signature | None:
    """Create carving signature when table type supports it."""
    if not isinstance(master_schema_entry, OrdinaryTableRow):
        return None
    if master_schema_entry.without_row_id or master_schema_entry.internal_schema_object:
        return None
    return create_table_signature(
        master_schema_entry.name,
        bundle.version_history.versions[BASE_VERSION_NUMBER],
        bundle.version_history,
    )


def recover_live_records(
    bundle: ArtifactBundle,
    table_names: list[str] | None = None,
) -> list[NormalizedRecord]:
    """Extract all live rows from the base database version."""
    records: list[NormalizedRecord] = []
    base_version = bundle.version_history.versions[BASE_VERSION_NUMBER]
    text_encoding = bundle.encoding
    source_sha256 = bundle.source_sha256

    for entry in base_version.master_schema.master_schema_entries:
        if entry.row_type != MASTER_SCHEMA_ROW_TYPE.TABLE:
            continue
        if entry.internal_schema_object:
            continue
        if table_names and entry.name not in table_names:
            continue
        if not entry.root_page_number:
            continue

        _number_of_cells, cells = aggregate_leaf_cells(
            base_version.get_b_tree_root_page(entry.root_page_number)
        )
        for cell in cells.values():
            records.append(
                cell_to_record(
                    cell,
                    entry,
                    source=RecordSource.LIVE,
                    algorithm="sqlite-dissect-live",
                    is_live=True,
                    is_deleted=False,
                    text_encoding=text_encoding,
                    source_sha256=source_sha256,
                    version=BASE_VERSION_NUMBER,
                )
            )
    return records


def recover_deleted_records(
    bundle: ArtifactBundle,
    *,
    table_names: list[str] | None = None,
    carve_freelist: bool = True,
    boyer_moore: bool = True,
) -> list[NormalizedRecord]:
    """Run all deletion recovery algorithms for supported tables."""
    records: list[NormalizedRecord] = []
    base_version = bundle.version_history.versions[BASE_VERSION_NUMBER]
    text_encoding = bundle.encoding
    source_sha256 = bundle.source_sha256

    for entry in base_version.master_schema.master_schema_entries:
        if entry.row_type != MASTER_SCHEMA_ROW_TYPE.TABLE:
            continue
        if entry.internal_schema_object:
            continue
        if table_names and entry.name not in table_names:
            continue
        if not entry.root_page_number:
            continue

        signature = _signature_for_table(bundle, entry)
        if signature is None:
            continue

        records.extend(
            recover_freeblocks(
                base_version,
                entry,
                signature,
                text_encoding=text_encoding,
                source_sha256=source_sha256,
            )
        )
        records.extend(
            recover_unallocated(
                base_version,
                entry,
                signature,
                text_encoding=text_encoding,
                source_sha256=source_sha256,
            )
        )
        if carve_freelist:
            records.extend(
                recover_freelist_pages(
                    base_version,
                    entry,
                    signature,
                    text_encoding=text_encoding,
                    source_sha256=source_sha256,
                )
            )
        if boyer_moore:
            records.extend(
                carve_pages_boyer_moore(
                    base_version,
                    entry,
                    signature,
                    text_encoding=text_encoding,
                    source_sha256=source_sha256,
                )
            )

        if bundle.rollback_journal is not None:
            records.extend(
                recover_journal_records(
                    bundle,
                    entry,
                    signature,
                    text_encoding=text_encoding,
                    source_sha256=source_sha256,
                )
            )

        parser = VersionHistoryParser(
            bundle.version_history,
            entry,
            None,
            None,
            signature,
            carve_freelist,
        )
        for commit in parser:
            for cell in commit.carved_cells.values():
                records.append(
                    cell_to_record(
                        cell,
                        entry,
                        source=RecordSource.CARVED,
                        algorithm="sqlite-dissect-version-carve",
                        is_live=False,
                        is_deleted=True,
                        text_encoding=text_encoding,
                        source_sha256=source_sha256,
                        version=commit.version_number,
                        confidence=0.9,
                    )
                )

    records.extend(
        recover_dropped_table_artifacts(
            bundle.database_path,
            bundle.page_size,
            source_sha256=bundle.source_sha256,
        )
    )
    return records


def _merge_provenance(
    target: NormalizedRecord,
    incoming: NormalizedRecord,
    seen_occurrence_ids: set[str],
) -> None:
    """Append unique provenances from incoming into target."""
    for provenance in incoming.provenances:
        occurrence = provenance.occurrence_id
        if occurrence and occurrence in seen_occurrence_ids:
            continue
        if occurrence:
            seen_occurrence_ids.add(occurrence)
        target.provenances.append(provenance)


def _aggregate_records(records: list[NormalizedRecord]) -> list[NormalizedRecord]:
    """Aggregate logical records and merge physical provenances."""
    grouped: dict[str, NormalizedRecord] = {}
    seen_occurrence: dict[str, set[str]] = {}

    for record in records:
        key = aggregate_key(record.table_name, record.row_id, record.columns)
        if key not in grouped:
            grouped[key] = NormalizedRecord(
                table_name=record.table_name,
                row_id=record.row_id,
                columns=record.columns,
                is_live=record.is_live,
                is_deleted=record.is_deleted,
                provenances=list(record.provenances),
            )
            seen_occurrence[key] = {
                p.occurrence_id for p in record.provenances if p.occurrence_id
            }
            continue

        grouped[key].is_live = grouped[key].is_live or record.is_live
        grouped[key].is_deleted = grouped[key].is_deleted or record.is_deleted
        _merge_provenance(grouped[key], record, seen_occurrence[key])

    return list(grouped.values())


def aggregate_record_confidence(provenances: list[Provenance]) -> float:
    """Compute record-level confidence.

    ``Provenance.source`` is authoritative over ``NormalizedRecord.is_live``.
    If any provenance is LIVE, the record confidence is 1.0; otherwise the
    maximum provenance confidence is used.
    """
    if any(provenance.source == RecordSource.LIVE for provenance in provenances):
        return 1.0
    if not provenances:
        return 0.0
    return max(provenance.confidence for provenance in provenances)


def finalize_records(
    records: list[NormalizedRecord],
    source_sha256: str,
) -> list[NormalizedRecord]:
    """Aggregate records and assign deterministic IDs and confidence."""
    aggregated = _aggregate_records(records)
    finalized: list[NormalizedRecord] = []
    for record in aggregated:
        record.record_id = derive_record_id(
            source_sha256=source_sha256,
            table_name=record.table_name,
            row_id=record.row_id,
            columns=record.columns,
        )
        record.confidence = aggregate_record_confidence(record.provenances)
        record.is_live = any(
            provenance.source == RecordSource.LIVE for provenance in record.provenances
        )
        record.is_deleted = not record.is_live
        finalized.append(record)
    return finalized
