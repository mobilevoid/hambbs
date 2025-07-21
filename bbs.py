import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path
import tempfile

from db import init_db, connect
from sync import SyncEngine

DB_PATH = Path('openbbs.db')


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

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
