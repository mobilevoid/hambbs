import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path('openbbs.db')

def connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH):
    conn = connect(db_path)
    cur = conn.cursor()
    # basic threads table
    cur.execute(
        """CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    # messages now carry an updated_at field for merge logic
    cur.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            timestamp TEXT,
            updated_at TEXT,
            author TEXT,
            body TEXT
        )"""
    )
    # client outbox queue
    cur.execute(
        """CREATE TABLE IF NOT EXISTS outbox (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            body TEXT,
            queued_at TEXT
        )"""
    )
    # sync log for auditing operations
    cur.execute(
        """CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            op TEXT,
            timestamp TEXT,
            details TEXT
        )"""
    )
    conn.commit()
    conn.close()


def record_sync(db_path, op, details=""):
    """Insert a sync operation record."""
    conn = connect(db_path)
    conn.execute(
        "INSERT INTO sync_log (op, timestamp, details) VALUES (?,?,?)",
        (op, datetime.utcnow().isoformat(), details),
    )
    conn.commit()
    conn.close()
