"""Corrupt DB salvage inspired by undark/sqbrite raw page carving."""

from __future__ import annotations

from pathlib import Path

from zeusdb.models import NormalizedRecord, Provenance, RecordSource


def salvage_raw_pages(
    database_path: str | Path,
    *,
    page_size: int = 4096,
    min_nonzero_ratio: float = 0.01,
) -> list[NormalizedRecord]:
    """Scan raw page bytes and emit salvage artifacts for non-empty regions.

    Args:
        database_path: Path to a potentially corrupt SQLite file.
        page_size: Page size to assume when header is unreadable.
        min_nonzero_ratio: Minimum ratio of non-zero bytes to report a region.

    Returns:
        Salvage artifact records with byte region metadata.
    """
    path = Path(database_path)
    raw = path.read_bytes()
    if len(raw) >= 16 and raw[0:16] == b"SQLite format 3\x00":
        page_size = int.from_bytes(raw[16:18], "big") or page_size

    records: list[NormalizedRecord] = []
    total_pages = max(1, len(raw) // page_size)
    for page_index in range(total_pages):
        offset = page_index * page_size
        page = raw[offset : offset + page_size]
        if not page:
            continue
        nonzero = sum(1 for b in page if b != 0)
        ratio = nonzero / len(page)
        if ratio < min_nonzero_ratio:
            continue
        records.append(
            NormalizedRecord(
                table_name="__salvage__",
                columns={
                    "page_number": page_index + 1,
                    "nonzero_bytes": nonzero,
                    "sample_hex": page[:32].hex(),
                },
                is_live=False,
                is_deleted=True,
                provenance=Provenance(
                    source=RecordSource.SALVAGE,
                    algorithm="undark-sqbrite-raw-page-scan",
                    page_number=page_index + 1,
                    file_offset=offset,
                    confidence=min(0.5 + ratio / 2, 0.95),
                    notes="Non-empty page region salvaged from raw file",
                ),
            )
        )
    return records
