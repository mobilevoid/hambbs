from flask import Blueprint, request, jsonify
from pathlib import Path
from db import connect, init_db
import uuid
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')
DB_PATH = Path('openbbs.db')


def get_conn():
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    return conn

@api_bp.route('/threads', methods=['GET', 'POST'])
def threads():
    conn = get_conn()
    cur = conn.cursor()
    if request.method == 'POST':
        data = request.get_json(force=True)
        tid = data.get('id') or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (tid, data['title'], now, now),
        )
        conn.commit()
        conn.close()
        return jsonify({'id': tid})
    rows = cur.execute("SELECT id, title, updated_at FROM threads ORDER BY updated_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@api_bp.route('/threads/<tid>', methods=['GET'])
def thread_detail(tid):
    conn = get_conn()
    cur = conn.cursor()
    thread = cur.execute("SELECT id, title, updated_at FROM threads WHERE id=?", (tid,)).fetchone()
    if not thread:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    msgs = cur.execute("SELECT * FROM messages WHERE thread_id=? ORDER BY timestamp", (tid,)).fetchall()
    conn.close()
    return jsonify({'thread': dict(thread), 'messages': [dict(m) for m in msgs]})

@api_bp.route('/threads/<tid>/messages', methods=['POST'])
def post_message(tid):
    conn = get_conn()
    cur = conn.cursor()
    data = request.get_json(force=True)
    mid = data.get('id') or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO messages (id, thread_id, timestamp, updated_at, author, body) VALUES (?,?,?,?,?,?)",
        (mid, tid, now, now, data.get('author'), data.get('body', '')),
    )
    cur.execute(
        "UPDATE threads SET updated_at=? WHERE id=?",
        (now, tid),
    )
    conn.commit()
    conn.close()
    return jsonify({'id': mid})
