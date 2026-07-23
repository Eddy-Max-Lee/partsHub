from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

@contextmanager
def connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()

def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with connection() as con:
        return [dict(row) for row in con.execute(sql, params)]

def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    with connection() as con:
        row = con.execute(sql, params).fetchone()
        return dict(row) if row else None
