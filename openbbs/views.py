from flask import Blueprint, render_template, request, redirect, url_for, current_app, send_from_directory, send_file
import gzip
import tempfile
import io
from cryptography.fernet import Fernet
from flask_login import login_required, current_user
from datetime import datetime
import hmac
import hashlib
from .models import Post, Forum, Attachment, User, Flag, PostVersion
from . import db
from werkzeug.utils import secure_filename
from pathlib import Path
import markdown

main_bp = Blueprint('main', __name__)


def _fernet() -> Fernet:
    """Return a Fernet instance using the app's encryption key."""
    key = current_app.config['ENCRYPTION_KEY']
    return Fernet(key)


def encrypt_attachment(data: bytes) -> bytes:
    compressed = gzip.compress(data)
    return _fernet().encrypt(compressed)


def decrypt_attachment(data: bytes) -> bytes:
    decrypted = _fernet().decrypt(data)
    return gzip.decompress(decrypted)


def _can_modify(post: Post) -> bool:
    """Return True if current user can edit or delete the post."""
    if not current_user.is_authenticated:
        return False
    if current_user.is_moderator:
        return True
    return post.user_id == current_user.id


def generate_action_token(post_id: int, user_id: int | None = None) -> str:
    """Return a signed token for actions on a post."""
    if user_id is None:
        user_id = current_user.id
    key = current_app.config['SECRET_KEY'].encode()
    msg = f"{post_id}:{user_id}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_action_token(post_id: int, token: str, user_id: int | None = None) -> bool:
    if user_id is None:
        user_id = current_user.id
    expected = generate_action_token(post_id, user_id)
    return hmac.compare_digest(expected, token or "")


def generate_owner_token(post_id: int, user_id: int) -> str:
    """Return a signed token representing permanent thread ownership."""
    key = current_app.config['SECRET_KEY'].encode()
    msg = f"owner:{post_id}:{user_id}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_owner_token(post: Post) -> bool:
    """Verify the stored owner token for a root post."""
    if not post.owner_token:
        return False
    expected = generate_owner_token(post.id, post.user_id)
    return hmac.compare_digest(expected, post.owner_token)


@main_bp.route('/preview', methods=['POST'])
@login_required
def preview_markdown():
    """Return HTML preview for provided markdown text."""
    text = request.get_json(force=True).get('text', '')
    html = markdown.markdown(text)
    return {'html': html}




@main_bp.route('/')
@login_required
def index():
    forums = Forum.query.all()
    return render_template('forums.html', forums=forums)


@main_bp.route('/post', methods=['POST'])
@login_required
def create_post():
    title = request.form.get('title')
    body = request.form.get('body')
    forum_id = request.form.get('forum_id', type=int)
    parent_id = request.form.get('parent_id', type=int)
    if title and body and forum_id:
        post = Post(title=title, body=body, author=current_user,
                    forum_id=forum_id, parent_id=parent_id)
        db.session.add(post)
        db.session.flush()  # to get id before committing
        if parent_id is None:
            post.owner_token = generate_owner_token(post.id, current_user.id)
        file = request.files.get('attachment')
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
            dest = upload_folder / f"{post.id}_{filename}.gz.enc"
            data = file.read()
            enc = encrypt_attachment(data)
            with open(dest, 'wb') as f:
                f.write(enc)
            att = Attachment(filename=str(dest), original_name=filename, post=post)
            db.session.add(att)
        db.session.commit()
        try:
            from .forums import get_forum_posts
            get_forum_posts.cache_clear()
        except Exception:
            pass
    if forum_id:
        return redirect(url_for('forums.view_forum', forum_id=forum_id))
    return redirect(url_for('main.index'))


@main_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not _can_modify(post) or post.deleted:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    if request.method == 'POST':
        token = request.form.get('token')
        if not verify_action_token(post.id, token):
            return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
        title = request.form.get('title')
        body = request.form.get('body')
        if title and body:
            ver = PostVersion(title=post.title, body=post.body, post=post)
            db.session.add(ver)
            post.title = title
            post.body = body
            post.edited_at = datetime.utcnow()
            db.session.commit()
            try:
                from .forums import get_forum_posts
                get_forum_posts.cache_clear()
            except Exception:
                pass
            return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = generate_action_token(post.id)
    return render_template('edit_post.html', post=post, token=token)


@main_bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not _can_modify(post):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    def _delete_recursive(p: Post, hard: bool):
        for child in list(p.children):
            _delete_recursive(child, hard)
        if hard:
            for att in list(p.attachments):
                try:
                    Path(att.filename).unlink(missing_ok=True)
                except Exception:
                    pass
                db.session.delete(att)
            db.session.delete(p)
        else:
            p.deleted = True

    _delete_recursive(post, current_user.is_moderator)
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('forums.view_forum', forum_id=post.forum_id))


@main_bp.route('/post/<int:post_id>/restore', methods=['POST'])
@login_required
def restore_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.is_moderator:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('main.trash'))
    post.deleted = False
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('main.trash'))


@main_bp.route('/post/<int:post_id>/history')
@login_required
def post_history(post_id):
    post = Post.query.get_or_404(post_id)
    if post.deleted:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    versions = PostVersion.query.filter_by(post_id=post.id).order_by(PostVersion.timestamp.desc()).all()
    token = generate_action_token(post.id)
    return render_template('history.html', post=post, versions=versions, token=token)


@main_bp.route('/post/<int:post_id>/revert/<int:ver_id>', methods=['POST'])
@login_required
def revert_post(post_id, ver_id):
    post = Post.query.get_or_404(post_id)
    if not _can_modify(post) or post.deleted:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    ver = PostVersion.query.get_or_404(ver_id)
    if ver.post_id != post.id:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    new_ver = PostVersion(title=post.title, body=post.body, post=post)
    db.session.add(new_ver)
    post.title = ver.title
    post.body = ver.body
    post.edited_at = datetime.utcnow()
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('main.post_history', post_id=post.id))


@main_bp.route('/post/<int:post_id>/flag', methods=['POST'])
@login_required
def flag_post(post_id):
    post = Post.query.get_or_404(post_id)
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    reason = request.form.get('reason') or ''
    flag = Flag(post=post, reporter=current_user, reason=reason)
    db.session.add(flag)
    db.session.commit()
    return redirect(url_for('forums.view_forum', forum_id=post.forum_id))


@main_bp.route('/post/<int:post_id>/pin', methods=['POST'])
@login_required
def pin_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.is_moderator or post.parent_id is not None:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    post.is_pinned = True
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('forums.view_forum', forum_id=post.forum_id))


@main_bp.route('/post/<int:post_id>/unpin', methods=['POST'])
@login_required
def unpin_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.is_moderator or post.parent_id is not None:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    post.is_pinned = False
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('forums.view_forum', forum_id=post.forum_id))


@main_bp.route('/post/<int:post_id>/lock', methods=['POST'])
@login_required
def lock_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.parent_id is not None:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    allowed = current_user.is_moderator or (current_user.id == post.user_id and verify_owner_token(post))
    if not allowed:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    post.is_locked = True
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('forums.view_forum', forum_id=post.forum_id))


@main_bp.route('/post/<int:post_id>/unlock', methods=['POST'])
@login_required
def unlock_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.parent_id is not None:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    allowed = current_user.is_moderator or (current_user.id == post.user_id and verify_owner_token(post))
    if not allowed:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    token = request.form.get('token')
    if not verify_action_token(post.id, token):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    post.is_locked = False
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('forums.view_forum', forum_id=post.forum_id))


@main_bp.route('/post/<int:post_id>/move', methods=['GET', 'POST'])
@login_required
def move_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.parent_id is not None:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    if not current_user.is_moderator:
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    if request.method == 'POST':
        token = request.form.get('token')
        if not verify_action_token(post.id, token):
            return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
        forum_id = request.form.get('forum_id', type=int)
        forum = Forum.query.get(forum_id)
        if forum:
            def _move_recursive(p: Post):
                p.forum_id = forum_id
                for child in p.children:
                    _move_recursive(child)
            _move_recursive(post)
            db.session.commit()
            try:
                from .forums import get_forum_posts
                get_forum_posts.cache_clear()
            except Exception:
                pass
            return redirect(url_for('forums.view_forum', forum_id=forum_id))
    forums = Forum.query.all()
    token = generate_action_token(post.id)
    return render_template('move_post.html', post=post, forums=forums, token=token)


@main_bp.route('/attachment/<int:att_id>')
@login_required
def get_attachment(att_id):
    """Return the attachment file, decrypting and decompressing if needed."""
    att = Attachment.query.get_or_404(att_id)
    path = Path(att.filename)
    if path.suffix == '.enc':
        data = path.read_bytes()
        data = decrypt_attachment(data)
        return send_file(io.BytesIO(data), as_attachment=True,
                         download_name=att.original_name)
    if path.suffix == '.gz':
        with gzip.open(path, 'rb') as f:
            data = f.read()
        return send_file(io.BytesIO(data), as_attachment=True,
                         download_name=att.original_name)
    return send_from_directory(path.parent, path.name, as_attachment=True,
                               download_name=att.original_name)


@main_bp.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id, deleted=False).order_by(Post.timestamp.desc()).all()
    thread_id = request.args.get('thread_id', type=int)
    owner = False
    if thread_id:
        thread = Post.query.get(thread_id)
        if thread and thread.parent_id is None and thread.user_id == current_user.id:
            owner = verify_owner_token(thread)
    token = generate_action_token(user.id)
    return render_template('profile.html', user=user, posts=posts, token=token, owner=owner, thread_id=thread_id)


@main_bp.route('/user/<int:user_id>/toggle_mod', methods=['POST'])
@login_required
def toggle_mod(user_id):
    thread_id = request.form.get('thread_id', type=int)
    allowed = current_user.is_moderator
    if not allowed and thread_id:
        thread = Post.query.get(thread_id)
        if thread and thread.parent_id is None and thread.user_id == current_user.id:
            allowed = verify_owner_token(thread)
    if not allowed:
        return redirect(url_for('main.profile', username=current_user.username))
    user = User.query.get_or_404(user_id)
    token = request.form.get('token')
    if not verify_action_token(user.id, token):
        return redirect(url_for('main.profile', username=user.username))
    user.is_moderator = not user.is_moderator
    db.session.commit()
    args = {}
    if thread_id:
        args['thread_id'] = thread_id
    return redirect(url_for('main.profile', username=user.username, **args))


@main_bp.route('/trash')
@login_required
def trash():
    if not current_user.is_moderator:
        return redirect(url_for('main.index'))
    posts = Post.query.filter_by(deleted=True).order_by(Post.timestamp.desc()).all()
    return render_template('trash.html', posts=posts)


@main_bp.route('/flags')
@login_required
def flags():
    if not current_user.is_moderator:
        return redirect(url_for('main.index'))
    flags = Flag.query.filter_by(resolved=False).order_by(Flag.timestamp.desc()).all()
    return render_template('flags.html', flags=flags)


@main_bp.route('/flag/<int:flag_id>/resolve', methods=['POST'])
@login_required
def resolve_flag(flag_id):
    if not current_user.is_moderator:
        return redirect(url_for('main.index'))
    flg = Flag.query.get_or_404(flag_id)
    flg.resolved = True
    db.session.commit()
    return redirect(url_for('main.flags'))


@main_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    author_q = request.args.get('author', '').strip()
    forum_id = request.args.get('forum_id', type=int)
    start = request.args.get('start')
    end = request.args.get('end')
    sort = request.args.get('sort', 'newest')
    results = []
    if query:
        like = f"%{query}%"
        q = Post.query.filter(
            (Post.title.ilike(like) | Post.body.ilike(like)) & (Post.deleted == False)
        )
        if forum_id:
            q = q.filter(Post.forum_id == forum_id)
        if start:
            try:
                dt = datetime.fromisoformat(start)
                q = q.filter(Post.timestamp >= dt)
            except ValueError:
                pass
        if end:
            try:
                dt = datetime.fromisoformat(end)
                q = q.filter(Post.timestamp <= dt)
            except ValueError:
                pass
        if author_q:
            user = User.query.filter(User.username.ilike(author_q)).first()
            if user:
                q = q.filter(Post.user_id == user.id)
        if sort == 'oldest':
            q = q.order_by(Post.timestamp.asc())
        elif sort == 'replies':
            from sqlalchemy import func
            q = q.outerjoin(Post.children).group_by(Post.id).order_by(func.count(Post.id).desc())
        else:
            q = q.order_by(Post.timestamp.desc())
        results = q.all()
    forums = Forum.query.all()
    return render_template('search.html', query=query, results=results, forums=forums, sort=sort)
