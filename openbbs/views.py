from flask import Blueprint, render_template, request, redirect, url_for, current_app, send_from_directory
from flask_login import login_required, current_user
from .models import Post, Forum, Attachment, User, Upvote

from .models import Post, Forum, Attachment, User
main
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

@main_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        bio = request.form.get('bio', '')
        current_user.bio = bio
        db.session.commit()
        return redirect(url_for('main.profile', username=current_user.username))
    return render_template('edit_profile.html', user=current_user)


@main_bp.route('/upvote/<int:post_id>', methods=['POST'])
@login_required
def upvote(post_id):
    post = Post.query.get_or_404(post_id)
    existing = Upvote.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if not existing:
        up = Upvote(user_id=current_user.id, post_id=post_id)
        db.session.add(up)
        post.author.reputation += 1
        db.session.commit()
    return redirect(request.referrer or url_for('main.index'))
main
