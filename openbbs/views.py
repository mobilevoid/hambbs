from flask import Blueprint, render_template, request, redirect, url_for, current_app, send_from_directory, send_file
import gzip
import tempfile
import io
from cryptography.fernet import Fernet
from flask_login import login_required, current_user
from datetime import datetime
from .models import Post, Forum, Attachment, User
from . import db
from werkzeug.utils import secure_filename
from pathlib import Path

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
        title = request.form.get('title')
        body = request.form.get('body')
        if title and body:
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
    return render_template('edit_post.html', post=post)


@main_bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not _can_modify(post):
        return redirect(url_for('forums.view_forum', forum_id=post.forum_id))
    if current_user.is_moderator:
        db.session.delete(post)
    else:
        post.deleted = True
    db.session.commit()
    try:
        from .forums import get_forum_posts
        get_forum_posts.cache_clear()
    except Exception:
        pass
    return redirect(url_for('forums.view_forum', forum_id=post.forum_id))


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
    return render_template('profile.html', user=user, posts=posts)


@main_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    author_q = request.args.get('author', '').strip()
    results = []
    if query:
        like = f"%{query}%"
        q = Post.query.filter(
            (Post.title.ilike(like) | Post.body.ilike(like)) & (Post.deleted == False)
        )
        if author_q:
            user = User.query.filter(User.username.ilike(author_q)).first()
            if user:
                q = q.filter(Post.user_id == user.id)
        results = q.order_by(Post.timestamp.desc()).all()
    return render_template('search.html', query=query, results=results)
