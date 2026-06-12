"""HTTP service for AISSS worker integration."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

from zeusdb.engine import AnalyzeOptions, ForensicEngine
from zeusdb.output.json_export import result_to_json_string

app = FastAPI(title="ZEUS-DB", version="0.1.0")
engine = ForensicEngine()


class AnalyzeRequest(BaseModel):
    """JSON analyze request for pre-staged files."""

    database_path: str
    wal_path: str | None = None
    journal_path: str | None = None
    carve: bool = True
    salvage: bool = False
    tables: list[str] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "zeus-db"}


@app.post("/analyze/path")
def analyze_path(request: AnalyzeRequest) -> dict:
    """Analyze SQLite files already on disk (container volume mount)."""
    options = AnalyzeOptions(
        carve=request.carve,
        salvage=request.salvage,
        tables=request.tables,
        wal_path=request.wal_path,
        journal_path=request.journal_path,
    )
    result = engine.analyze(request.database_path, options)
    return result.to_dict()


@app.post("/analyze/upload")
async def analyze_upload(
    database: UploadFile = File(...),
    wal: UploadFile | None = File(None),
    journal: UploadFile | None = File(None),
    carve: bool = Form(True),
    salvage: bool = Form(False),
) -> dict:
    """Analyze uploaded SQLite artifacts into a temp workspace."""
    with tempfile.TemporaryDirectory(prefix="zeusdb-") as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / (database.filename or "upload.db")
        db_path.write_bytes(await database.read())

        wal_path: Path | None = None
        if wal is not None:
            wal_path = tmp_path / (wal.filename or "upload.db-wal")
            wal_path.write_bytes(await wal.read())

        journal_path: Path | None = None
        if journal is not None:
            journal_path = tmp_path / (journal.filename or "upload.db-journal")
            journal_path.write_bytes(await journal.read())

        options = AnalyzeOptions(
            carve=carve,
            salvage=salvage,
            wal_path=str(wal_path) if wal_path else None,
            journal_path=str(journal_path) if journal_path else None,
        )
        result = engine.analyze(db_path, options)
        return result.to_dict()


@app.post("/analyze/text")
def analyze_text_summary(request: AnalyzeRequest) -> dict[str, str]:
    """Return plain-text summary suitable for AISSS ingestion."""
    options = AnalyzeOptions(
        carve=request.carve,
        salvage=request.salvage,
        tables=request.tables,
        wal_path=request.wal_path,
        journal_path=request.journal_path,
    )
    result = engine.analyze(request.database_path, options)
    lines: list[str] = [
        f"# ZEUS-DB analysis: {result.database_path}",
        f"Tables: {', '.join(result.tables)}",
        "",
    ]
    for record in result.records:
        cols = ", ".join(f"{k}={v!r}" for k, v in record.columns.items())
        lines.append(
            f"[{record.provenance.source.value}] {record.table_name} "
            f"row_id={record.row_id} {cols}"
        )
    return {"text": "\n".join(lines), "json": result_to_json_string(result)}
