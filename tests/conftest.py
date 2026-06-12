"""Shared test fixtures."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    """Create a synthetic DB with one deleted row."""
    db_path = tmp_path / "sample.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.executemany(
        "INSERT INTO users VALUES (?, ?, ?)",
        [
            (1, "Alice", "alice@lab.local"),
            (2, "Bob", "bob@lab.local"),
            (3, "Carol", "carol@lab.local"),
        ],
    )
    conn.commit()
    conn.execute("DELETE FROM users WHERE id = 1")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def wal_db(tmp_path: Path) -> tuple[Path, Path]:
    """Create DB in WAL mode; sidecar may exist depending on checkpoint behavior."""
    db_path = tmp_path / "walcase.db"
    wal_path = tmp_path / "walcase.db-wal"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, action TEXT)")
    conn.execute("INSERT INTO events VALUES (1, 'login')")
    conn.commit()
    conn.execute("INSERT INTO events VALUES (2, 'logout')")
    conn.commit()
    conn.close()
    return db_path, wal_path
