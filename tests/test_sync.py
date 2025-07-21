import os
import tempfile
from pathlib import Path

from db import init_db, connect
from sync import SyncEngine
import bbs
from bbs import cmd_queue_post, cmd_outbox_view


def setup_db():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    init_db(db_path)
    return db_path


def test_pull_push_cycle():
    db_path = setup_db()
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO threads (id, title, created_at, updated_at) VALUES (?,?,?,?)",
                ('t1', 'Thread', '2023-01-01T00:00:00', '2023-01-01T00:00:00'))
    cur.execute("INSERT INTO messages (id, thread_id, timestamp, updated_at, author, body) VALUES (?,?,?,?,?,?)",
                ('m1', 't1', '2023-01-01T00:00:00', '2023-01-01T00:00:00', 'alice', 'hello'))
    conn.commit()
    engine = SyncEngine(db_path)
    pkg = tempfile.NamedTemporaryFile(suffix='.tar.zst', delete=False).name
    engine.pull(output_path=pkg)
    cur.execute('DELETE FROM messages')
    cur.execute('DELETE FROM threads')
    conn.commit()
    summary = engine.push(pkg)
    cur2 = conn.cursor()
    t = cur2.execute('SELECT * FROM threads').fetchone()
    m = cur2.execute('SELECT * FROM messages').fetchone()
    assert t['id'] == 't1'
    assert m['id'] == 'm1'
    assert summary['threads'] == 1
    assert summary['messages'] == 1
    Path(pkg).unlink()


def test_outbox_queue_and_view(capsys):
    db_path = setup_db()
    bbs.DB_PATH = Path(db_path)
    bbs.CONF['db_path'] = db_path
    args = type('obj', (object,), {'thread_id': 't1', 'body': 'message body'})
    cmd_queue_post(args)
    view_args = type('obj', (object,), {})
    cmd_outbox_view(view_args)
    captured = capsys.readouterr()
    assert 'message body' in captured.out
