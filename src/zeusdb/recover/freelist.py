"""Freelist page recovery (bring2lite freelist trunk/leaf processing)."""

from __future__ import annotations

from typing import Any

from sqlite_dissect.carving.carver import SignatureCarver
from sqlite_dissect.constants import CELL_SOURCE, PAGE_TYPE

from zeusdb.models import NormalizedRecord, RecordSource
from zeusdb.recover.convert import cell_to_record


def recover_freelist_pages(
    version: Any,
    master_schema_entry: Any,
    signature: Any,
    *,
    text_encoding: str = "UTF-8",
) -> list[NormalizedRecord]:
    """Carve deleted records from freelist trunk and leaf pages."""
    records: list[NormalizedRecord] = []
    trunk_number = version.database_header.first_freelist_trunk_page_number

    while trunk_number:
        trunk_page = version.get_page(trunk_number)
        if trunk_page.page_type == PAGE_TYPE.FREELIST_TRUNK:
            for leaf_page in trunk_page.freelist_leaf_pages:
                records.extend(
                    _carve_freelist_page(
                        version,
                        leaf_page,
                        master_schema_entry,
                        signature,
                        text_encoding=text_encoding,
                    )
                )
            trunk_number = trunk_page.next_freelist_trunk_page_number
        elif trunk_page.page_type == PAGE_TYPE.FREELIST_LEAF:
            records.extend(
                _carve_freelist_page(
                    version,
                    trunk_page,
                    master_schema_entry,
                    signature,
                    text_encoding=text_encoding,
                )
            )
            break
        else:
            break

    return records


def _carve_freelist_page(
    version: Any,
    page: Any,
    master_schema_entry: Any,
    signature: Any,
    *,
    text_encoding: str = "UTF-8",
) -> list[NormalizedRecord]:
    """Carve unallocated bytes on a freelist page."""
    records: list[NormalizedRecord] = []
    unallocated = getattr(page, "unallocated_space", b"")
    start_offset = getattr(page, "unallocated_space_start_offset", 0)
    if not unallocated:
        return records

    carved = SignatureCarver.carve_unallocated_space(
        version,
        CELL_SOURCE.FREELIST,
        page.number,
        start_offset,
        unallocated,
        signature,
    )
    for cell in carved:
        records.append(
            cell_to_record(
                cell,
                master_schema_entry,
                source=RecordSource.FREELIST,
                algorithm="bring2lite-freelist+sqlite-dissect",
                is_live=False,
                is_deleted=True,
                text_encoding=text_encoding,
                version=getattr(version, "version_number", 0),
                confidence=0.75,
            )
        )
    return records
