from . import db, login_manager
from flask_login import UserMixin
from datetime import datetime


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    bio = db.Column(db.Text, default="")
    reputation = db.Column(db.Integer, default=0)
    is_moderator = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author', lazy=True)


class Forum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    posts = db.relationship('Post', backref='forum', lazy=True)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    forum_id = db.Column(db.Integer, db.ForeignKey('forum.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    children = db.relationship('Post', backref=db.backref('parent', remote_side=[id]), lazy=True)
    attachments = db.relationship('Attachment', backref='post', lazy=True)


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
