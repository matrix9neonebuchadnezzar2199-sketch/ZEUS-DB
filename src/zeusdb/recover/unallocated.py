"""Unallocated space recovery (bring2lite Algorithm 4 via sqlite-dissect)."""

from __future__ import annotations

from typing import Any

from sqlite_dissect.carving.carver import SignatureCarver
from sqlite_dissect.constants import CELL_SOURCE
from sqlite_dissect.file.database.page import BTreePage
from sqlite_dissect.file.database.utilities import get_pages_from_b_tree_page

from zeusdb.models import NormalizedRecord, RecordSource
from zeusdb.recover.convert import cell_to_record


def recover_unallocated(
    version: Any,
    master_schema_entry: Any,
    signature: Any,
    *,
    text_encoding: str = "UTF-8",
) -> list[NormalizedRecord]:
    """Recover deleted records from page unallocated regions."""
    records: list[NormalizedRecord] = []
    root_page = version.get_b_tree_root_page(master_schema_entry.root_page_number)
    for page in get_pages_from_b_tree_page(root_page):
        if not isinstance(page, BTreePage):
            continue
        carved = SignatureCarver.carve_unallocated_space(
            version,
            CELL_SOURCE.B_TREE,
            page.number,
            page.unallocated_space_start_offset,
            page.unallocated_space,
            signature,
        )
        for cell in carved:
            records.append(
                cell_to_record(
                    cell,
                    master_schema_entry,
                    source=RecordSource.UNALLOCATED,
                    algorithm="bring2lite-unallocated+sqlite-dissect",
                    is_live=False,
                    is_deleted=True,
                    text_encoding=text_encoding,
                    version=getattr(version, "version_number", 0),
                    confidence=0.8,
                )
            )
    return records
