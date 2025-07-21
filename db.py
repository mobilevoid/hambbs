import sqlite3
from pathlib import Path

DB_PATH = Path('openbbs.db')

def connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH):
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            timestamp TEXT,
            author TEXT,
            body TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS outbox (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            body TEXT,
            queued_at TEXT
        )"""
    )
    conn.commit()
    conn.close()
