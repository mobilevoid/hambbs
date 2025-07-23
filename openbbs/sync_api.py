import json
import tempfile
from flask import Blueprint, request, send_file, jsonify
from pathlib import Path
from . import db as sqldb  # SQLAlchemy instance not used but required for models
from sync import SyncEngine
from db import init_db
from functools import lru_cache

sync_bp = Blueprint('sync_api', __name__, url_prefix='/api/sync')

@lru_cache(maxsize=1)
def get_engine():
    db_path = Path('openbbs.db').resolve()
    init_db(db_path)
    return SyncEngine(str(db_path))

@sync_bp.route('/pull', methods=['POST'])
def pull_route():
    data = request.get_json(force=True, silent=True) or {}
    since = data.get('since')
    threads = data.get('threads')
    with tempfile.NamedTemporaryFile(suffix='.tar.zst', delete=False) as tmp:
        path = tmp.name
    engine = get_engine()
    engine.pull(since=since, thread_ids=threads, output_path=path)
    return send_file(path, as_attachment=True, download_name='sync.tar.zst')

@sync_bp.route('/push', methods=['POST'])
def push_route():
    file = request.files.get('file')
    if file:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        file.save(tmp)
        tmp.close()
        engine = get_engine()
        summary = engine.push(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)
        return jsonify(summary)
    if request.data:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(request.data)
        tmp.close()
        engine = get_engine()
        summary = engine.push(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)
        return jsonify(summary)
    return jsonify({'error': 'no file provided'}), 400
