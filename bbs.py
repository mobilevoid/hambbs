import argparse
import sys
import uuid
import json
from datetime import datetime
from pathlib import Path
import tempfile

from db import init_db, connect
from sync import SyncEngine
from radio import RadioInterface, VaraHFClient, KISSTnc

CONFIG_FILE = Path('config.json')
DEFAULT_CONFIG = {
    'db_path': 'openbbs.db',
    'server_url': 'http://localhost:5000'
}


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            conf = json.load(f)
            DEFAULT_CONFIG.update(conf)
    return DEFAULT_CONFIG


CONF = load_config()
DB_PATH = Path(CONF['db_path'])


def cmd_sync_pull(args):
    engine = SyncEngine(str(DB_PATH))
    with tempfile.NamedTemporaryFile(suffix='.tar.zst', delete=False) as tmp:
        path = tmp.name if args.output == '-' else args.output or tmp.name
    engine.pull(since=args.since, thread_ids=args.thread, output_path=path)
    if args.output == '-':
        with open(path, 'rb') as f:
            sys.stdout.buffer.write(f.read())
        Path(path).unlink(missing_ok=True)
    else:
        print(path)


def cmd_sync_push(args):
    engine = SyncEngine(str(DB_PATH))
    summary = engine.push(args.package)
    print(summary)


def cmd_list(_):
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    rows = conn.execute("SELECT id, title, updated_at FROM threads ORDER BY updated_at DESC").fetchall()
    for r in rows:
        print(r['id'], r['title'], r['updated_at'])
    conn.close()


def cmd_read(args):
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    t = conn.execute("SELECT title FROM threads WHERE id=?", (args.thread_id,)).fetchone()
    if not t:
        print('thread not found')
        return
    print('#', t['title'])
    msgs = conn.execute("SELECT author, body, timestamp FROM messages WHERE thread_id=? ORDER BY timestamp", (args.thread_id,)).fetchall()
    for m in msgs:
        print(f"[{m['timestamp']}] {m['author']}: {m['body']}")
    conn.close()


def cmd_post(args):
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    mid = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO messages (id, thread_id, timestamp, updated_at, author, body) VALUES (?,?,?,?,?,?)",
        (mid, args.thread_id, ts, ts, args.author, args.body)
    )
    conn.execute("UPDATE threads SET updated_at=? WHERE id=?", (ts, args.thread_id))
    conn.commit()
    conn.close()
    print(mid)


def cmd_new_thread(args):
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    tid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?,?,?,?)",
        (tid, args.title, now, now)
    )
    conn.commit()
    conn.close()
    print(tid)


def cmd_queue_post(args):
    body = args.body
    if not body:
        body = sys.stdin.read()
    tid = args.thread_id
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    cur = conn.cursor()
    mid = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO outbox (id, thread_id, body, queued_at) VALUES (?,?,?,?)",
        (mid, tid, body, ts)
    )
    conn.commit()
    conn.close()
    print(mid)


def cmd_outbox_view(_):
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute("SELECT id, thread_id, queued_at, body FROM outbox ORDER BY queued_at").fetchall()
    for r in rows:
        snippet = r['body'][:80].replace('\n', ' ')
        print(f"{r['id']} {r['thread_id']} {r['queued_at']} {snippet}")
    conn.close()


def _create_iface(mode, port):
    if mode == 'varahf':
        host, *p = port.split(':')
        p = int(p[0]) if p else 8300
        return VaraHFClient(host, p)
    return RadioInterface(port)


def cmd_radio_send(args):
    iface = _create_iface(args.mode, args.port)
    if args.kiss:
        iface = KISSTnc(iface)
        iface.send_packet(args.message.encode('utf-8'))
    else:
        iface.send(args.message.encode('utf-8'))


def cmd_radio_recv(args):
    iface = _create_iface(args.mode, args.port)
    if args.kiss:
        iface = KISSTnc(iface)
        data = iface.receive_packet()
    else:
        data = iface.receive()
    sys.stdout.buffer.write(data)


def main():
    parser = argparse.ArgumentParser(description='Hambbs CLI')
    sub = parser.add_subparsers(dest='command')

    sync = sub.add_parser('sync')
    sync_sub = sync.add_subparsers(dest='sync_cmd')

    pull = sync_sub.add_parser('pull')
    pull.add_argument('--since')
    pull.add_argument('--thread', nargs='*')
    pull.add_argument('output', nargs='?', default='sync.tar.zst')
    pull.set_defaults(func=cmd_sync_pull)

    push = sync_sub.add_parser('push')
    push.add_argument('package')
    push.set_defaults(func=cmd_sync_push)

    queue = sub.add_parser('queue')
    queue_sub = queue.add_subparsers(dest='queue_cmd')

    qp = queue_sub.add_parser('post')
    qp.add_argument('thread_id')
    qp.add_argument('--body')
    qp.set_defaults(func=cmd_queue_post)

    outbox = sub.add_parser('outbox')
    outbox_sub = outbox.add_subparsers(dest='outbox_cmd')

    ov = outbox_sub.add_parser('view')
    ov.set_defaults(func=cmd_outbox_view)

    sub.add_parser('list').set_defaults(func=cmd_list)
    rd = sub.add_parser('read')
    rd.add_argument('thread_id')
    rd.set_defaults(func=cmd_read)
    post = sub.add_parser('post')
    post.add_argument('thread_id')
    post.add_argument('body')
    post.add_argument('--author', default='anon')
    post.set_defaults(func=cmd_post)
    nt = sub.add_parser('new')
    nt.add_argument('title')
    nt.set_defaults(func=cmd_new_thread)

    radio = sub.add_parser('radio')
    radio_sub = radio.add_subparsers(dest='radio_cmd')

    rs = radio_sub.add_parser('send')
    rs.add_argument('port')
    rs.add_argument('message')
    rs.add_argument('--mode', choices=['com', 'varahf'], default='com')
    rs.add_argument('--kiss', action='store_true', help='use KISS framing')
    rs.set_defaults(func=cmd_radio_send)

    rr = radio_sub.add_parser('recv')
    rr.add_argument('port')
    rr.add_argument('--mode', choices=['com', 'varahf'], default='com')
    rr.add_argument('--kiss', action='store_true', help='use KISS framing')
    rr.set_defaults(func=cmd_radio_recv)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
