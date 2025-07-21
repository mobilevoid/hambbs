import json
import logging
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime
import zstandard as zstd

from db import connect, init_db, record_sync

logger = logging.getLogger('sync')
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler('sync.log')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

class SyncEngine:
    def __init__(self, db_path='openbbs.db'):
        self.db_path = db_path
        init_db(db_path)

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def pull(self, since=None, thread_ids=None, output_path='sync.tar.zst'):
        """Export threads/messages newer than *since* to a compressed package."""
        logger.info('Starting pull operation')
        record_sync(self.db_path, 'pull', f'since={since}')
        conn = self._conn()
        cur = conn.cursor()
        params = []
        query = "SELECT * FROM threads"
        conditions = []
        if since:
            conditions.append("updated_at >= ?")
            params.append(since)
        if thread_ids:
            placeholders = ','.join('?' for _ in thread_ids)
            conditions.append(f"id IN ({placeholders})")
            params.extend(thread_ids)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        threads = cur.execute(query, params).fetchall()
        base = Path(tempfile.mkdtemp())
        (base / 'threads').mkdir()
        index = []
        for t in threads:
            index.append({
                'id': t['id'],
                'title': t['title'],
                'created_at': t['created_at'],
                'updated_at': t['updated_at'],
            })
            msgs = cur.execute(
                "SELECT * FROM messages WHERE thread_id=?" + (" AND updated_at>=?" if since else ""),
                [t['id']] + ([since] if since else [])
            ).fetchall()
            msgs_data = [dict(m) for m in msgs]
            with open(base / 'threads' / f"{t['id']}.json", 'w') as f:
                json.dump(msgs_data, f)
        with open(base / 'index.json', 'w') as f:
            json.dump(index, f)
        tar_path = base / 'package.tar'
        with tarfile.open(tar_path, 'w') as tar:
            tar.add(base / 'index.json', arcname='index.json')
            tar.add(base / 'threads', arcname='threads')
        compressor = zstd.ZstdCompressor()
        with open(tar_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            f_out.write(compressor.compress(f_in.read()))
        logger.info('Pull completed: %s', output_path)
        return output_path

    def push(self, package_path):
        logger.info('Starting push operation')
        record_sync(self.db_path, 'push', package_path)
        base = Path(tempfile.mkdtemp())
        tar_path = base / 'package.tar'
        decompressor = zstd.ZstdDecompressor()
        with open(package_path, 'rb') as f_in, open(tar_path, 'wb') as f_out:
            f_out.write(decompressor.decompress(f_in.read()))
        with tarfile.open(tar_path, 'r') as tar:
            tar.extractall(base)
        with open(base / 'index.json') as f:
            index = json.load(f)
        conn = self._conn()
        cur = conn.cursor()
        imported_threads = 0
        imported_msgs = 0
        for t in index:
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO threads (id, title, created_at, updated_at) VALUES (?,?,?,?)",
                    (t['id'], t['title'], t['created_at'], t['updated_at'])
                )
                if cur.rowcount:
                    imported_threads += 1
            except sqlite3.IntegrityError:
                pass
            msgs_path = base / 'threads' / f"{t['id']}.json"
            if msgs_path.exists():
                with open(msgs_path) as mf:
                    msgs = json.load(mf)
                for m in msgs:
                    existing = cur.execute("SELECT updated_at FROM messages WHERE id=?", (m['id'],)).fetchone()
                    if existing:
                        if existing['updated_at'] and existing['updated_at'] >= m.get('updated_at', m['timestamp']):
                            continue
                        cur.execute(
                            "UPDATE messages SET thread_id=?, timestamp=?, updated_at=?, author=?, body=? WHERE id=?",
                            (m['thread_id'], m['timestamp'], m.get('updated_at', m['timestamp']), m.get('author'), m['body'], m['id'])
                        )
                    else:
                        cur.execute(
                            "INSERT INTO messages (id, thread_id, timestamp, updated_at, author, body) VALUES (?,?,?,?,?,?)",
                            (m['id'], m['thread_id'], m['timestamp'], m.get('updated_at', m['timestamp']), m.get('author'), m['body'])
                        )
                    imported_msgs += 1
                    # update thread timestamp whenever a message is newer
                    cur.execute(
                        "UPDATE threads SET updated_at=? WHERE id=? AND updated_at<?",
                        (m.get('updated_at', m['timestamp']), t['id'], m.get('updated_at', m['timestamp']))
                    )
        conn.commit()
        conn.close()
        logger.info('Push completed: %d threads, %d messages', imported_threads, imported_msgs)
        return {'threads': imported_threads, 'messages': imported_msgs}
