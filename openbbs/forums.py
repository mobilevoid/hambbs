from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from .models import Forum, Post
from . import db

forums_bp = Blueprint('forums', __name__, url_prefix='/forums')


@forums_bp.route('/')
@login_required
def list_forums():
    forums = Forum.query.all()
    return render_template('forums.html', forums=forums)


@forums_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_forum():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if name:
            f = Forum(name=name, description=description or '')
            db.session.add(f)
            db.session.commit()
            return redirect(url_for('forums.list_forums'))
    return render_template('create_forum.html')


@forums_bp.route('/<int:forum_id>')
@login_required
def view_forum(forum_id):
    forum = Forum.query.get_or_404(forum_id)
    posts = Post.query.filter_by(forum_id=forum_id, parent_id=None).order_by(Post.timestamp.desc()).all()
    return render_template('forum_view.html', forum=forum, posts=posts)
