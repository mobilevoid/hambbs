from flask import Blueprint, render_template, request, redirect, url_for, current_app, send_from_directory
from flask_login import login_required, current_user
from .models import Post, Forum, Attachment, User
from . import db
from werkzeug.utils import secure_filename
from pathlib import Path

main_bp = Blueprint('main', __name__)


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
            dest = upload_folder / f"{post.id}_{filename}"
            file.save(dest)
            att = Attachment(filename=str(dest), original_name=filename, post=post)
            db.session.add(att)
        db.session.commit()
    if forum_id:
        return redirect(url_for('forums.view_forum', forum_id=forum_id))
    return redirect(url_for('main.index'))


@main_bp.route('/attachment/<int:att_id>')
@login_required
def get_attachment(att_id):
    att = Attachment.query.get_or_404(att_id)
    path = Path(att.filename)
    return send_from_directory(path.parent, path.name, as_attachment=True,
                               download_name=att.original_name)


@main_bp.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    return render_template('profile.html', user=user, posts=posts)


@main_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []
    if query:
        like = f"%{query}%"
        results = Post.query.filter(
            Post.title.ilike(like) | Post.body.ilike(like)
        ).order_by(Post.timestamp.desc()).all()
    return render_template('search.html', query=query, results=results)
