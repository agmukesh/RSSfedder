from pathlib import Path
from uuid import uuid4

import pytest

import db


@pytest.fixture
def temp_db(monkeypatch):
    real_connect = db.sqlite3.connect

    def connect_without_journal(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        conn.execute("PRAGMA journal_mode=OFF")
        return conn

    tmp_dir = Path(__file__).parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"feeds_{uuid4().hex}.db"
    monkeypatch.setattr(db, "DB_FILE", str(db_path))
    monkeypatch.setattr(db.sqlite3, "connect", connect_without_journal)
    db.init_db()
    yield db_path
