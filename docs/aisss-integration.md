# AISSS Integration

ZEUS-DB 本体のアルゴリズム解説は [00-index.md](00-index.md) を参照。

## Service

- Container name: `zeus-db`
- Default URL: `http://zeus-db:8090`
- Health: `GET /health`

## Worker flow

1. Worker detects `.sqlite` / `.db` attachments (`attachment_kind=sqlite`).
2. Worker POSTs file to `POST /analyze/upload` with `carve=true`.
3. Response JSON (`schema_version=1.1`) is stored; `summary.text` field from `/analyze/text` is used as extracted text for RAG.

## JSON contract (excerpt)

```json
{
  "schema_version": "1.1",
  "database_path": "...",
  "metadata": {"source_sha256": "..."},
  "tables": ["users"],
  "timeline": [{"version": 0, "label": "base_database"}],
  "records": [{
    "record_id": "...",
    "table_name": "users",
    "confidence": 0.85,
    "columns": {"name": "Alice"},
    "provenances": [{
      "source": "freeblock",
      "algorithm": "bring2lite-freeblock+sqlite-dissect",
      "occurrence_id": "..."
    }]
  }],
  "summary": {"total_records": 10, "live_records": 2, "deleted_records": 8}
}
```

## Compose

Set `ZEUSDB_BUILD_CONTEXT` in `aisss/.env` to the ZEUS-DB repo path (sibling of Aisss by default).
