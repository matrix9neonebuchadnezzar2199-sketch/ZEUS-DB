"""Boyer-Moore page carving using schema serial-type fingerprints (fqlite concept)."""

from __future__ import annotations

from typing import Any

from sqlite_dissect.carving.utilities import generate_signature_regex
from sqlite_dissect.constants import CELL_SOURCE
from sqlite_dissect.file.database.page import BTreePage
from sqlite_dissect.file.database.utilities import get_pages_from_b_tree_page

from zeusdb.models import NormalizedRecord, RecordSource
from zeusdb.recover.convert import cell_to_record


def boyer_moore_search(haystack: bytes, needle: bytes) -> list[int]:
    """Find all occurrences of needle in haystack using Boyer-Moore bad-character rule."""
    if not needle or len(needle) > len(haystack):
        return []

    bad_char: dict[int, int] = {}
    for i, byte in enumerate(needle[:-1]):
        bad_char[byte] = len(needle) - 1 - i

    matches: list[int] = []
    index = 0
    while index <= len(haystack) - len(needle):
        j = len(needle) - 1
        while j >= 0 and haystack[index + j] == needle[j]:
            j -= 1
        if j < 0:
            matches.append(index)
            index += 1
        else:
            skip = bad_char.get(haystack[index + j], len(needle))
            index += max(1, skip - (len(needle) - 1 - j))
    return matches


def _signature_needle(signature: Any) -> bytes | None:
    """Build a byte needle from simplified schema signature regex."""
    simplified = signature.simplified_signature or signature.recommended_schema_signature
    if not simplified:
        return None
    pattern = generate_signature_regex(simplified, True)
    if not pattern or len(pattern) < 2:
        return None
    return pattern[: min(8, len(pattern))]


def carve_pages_boyer_moore(
    version: Any,
    master_schema_entry: Any,
    signature: Any,
    *,
    text_encoding: str = "UTF-8",
    source_sha256: str,
) -> list[NormalizedRecord]:
    """Scan raw page bytes for signature anchors and carve nearby cells."""
    from sqlite_dissect.carving.carver import SignatureCarver

    needle = _signature_needle(signature)
    if needle is None:
        return []

    records: list[NormalizedRecord] = []
    root_page = version.get_b_tree_root_page(master_schema_entry.root_page_number)
    for page in get_pages_from_b_tree_page(root_page):
        if not isinstance(page, BTreePage):
            continue
        page_bytes = version.get_page_data(page.number)
        for offset in boyer_moore_search(page_bytes, needle):
            tail = page_bytes[offset:]
            carved = SignatureCarver.carve_unallocated_space(
                version,
                CELL_SOURCE.B_TREE,
                page.number,
                offset,
                tail,
                signature,
            )
            for cell in carved:
                records.append(
                    cell_to_record(
                        cell,
                        master_schema_entry,
                        source=RecordSource.CARVED,
                        algorithm="fqlite-boyer-moore+sqlite-dissect",
                        is_live=False,
                        is_deleted=True,
                        text_encoding=text_encoding,
                        source_sha256=source_sha256,
                        version=getattr(version, "version_number", 0),
                        confidence=0.7,
                    )
                )
    return records
