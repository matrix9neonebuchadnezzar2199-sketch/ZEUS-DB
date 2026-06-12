"""Recovery orchestration across all algorithms."""

from __future__ import annotations

import json
from typing import Any

from sqlite_dissect.carving.signature import Signature
from sqlite_dissect.constants import BASE_VERSION_NUMBER, MASTER_SCHEMA_ROW_TYPE
from sqlite_dissect.file.database.utilities import aggregate_leaf_cells
from sqlite_dissect.file.schema.master import OrdinaryTableRow
from sqlite_dissect.interface import create_table_signature
from sqlite_dissect.version_history import VersionHistoryParser

from zeusdb.models import NormalizedRecord, RecordSource
from zeusdb.reader.database import ArtifactBundle
from zeusdb.recover.carver import carve_pages_boyer_moore
from zeusdb.recover.convert import cell_to_record
from zeusdb.recover.dropped_table import recover_dropped_table_artifacts
from zeusdb.recover.freeblock import recover_freeblocks
from zeusdb.recover.freelist import recover_freelist_pages
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

        records.extend(recover_freeblocks(base_version, entry, signature, text_encoding=text_encoding))
        records.extend(recover_unallocated(base_version, entry, signature, text_encoding=text_encoding))
        if carve_freelist:
            records.extend(
                recover_freelist_pages(base_version, entry, signature, text_encoding=text_encoding)
            )
        if boyer_moore:
            records.extend(
                carve_pages_boyer_moore(base_version, entry, signature, text_encoding=text_encoding)
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
                        version=commit.version_number,
                        confidence=0.9,
                    )
                )

    records.extend(
        recover_dropped_table_artifacts(bundle.database_path, bundle.page_size)
    )
    return _dedupe_records(records)


def _dedupe_records(records: list[NormalizedRecord]) -> list[NormalizedRecord]:
    """Remove duplicate recovered rows by content fingerprint."""
    seen: set[str] = set()
    unique: list[NormalizedRecord] = []
    for record in records:
        key = f"{record.table_name}|{record.row_id}|{sorted(record.columns.items())}|{record.provenance.source}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique
