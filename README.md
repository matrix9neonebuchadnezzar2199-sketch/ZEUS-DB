# ZEUS-DB

Unified SQLite forensic analysis engine for lab environments.

Built on [DC3 sqlite-dissect](https://github.com/dod-cyber-crime-center/sqlite-dissect) with additional recovery algorithms inspired by bring2lite, fqlite, xsqlite, undark, and sqbrite (concept reimplementation only).

## Features

- Read-only parsing of SQLite database, WAL, and rollback journal
- Version-timeline across WAL commit records
- Deleted record recovery: freeblocks, unallocated space, freelist pages
- Schema fingerprint carving (Boyer-Moore page scan)
- Dropped table artifact scanning
- Corrupt DB salvage (raw page carving)
- JSON / TSV / CASE export with provenance metadata
- HTTP service for AISSS worker integration

## Quick start

```powershell
uv sync --all-groups
uv run zeusdb analyze tests/fixtures/sample.db --json output.json --carve
uv run pytest
```

## HTTP service

```powershell
uv run uvicorn service.app:app --host 0.0.0.0 --port 8090
```

## License

MIT (ZEUS-DB). Third-party: see `THIRD_PARTY_NOTICES.md` (sqlite-dissect DC3 license).
