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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship("Post", backref="author", lazy=True)
    flags = db.relationship("Flag", backref="reporter", lazy=True)
    received_notes = db.relationship(
        "ModNote", foreign_keys="ModNote.user_id", backref="target", lazy=True
    )
    sent_notes = db.relationship(
        "ModNote", foreign_keys="ModNote.mod_id", backref="moderator", lazy=True
    )


class Forum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    posts = db.relationship("Post", backref="forum", lazy=True)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean, default=False)
    delete_reason = db.Column(db.String(255))
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    owner_token = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    forum_id = db.Column(db.Integer, db.ForeignKey("forum.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    children = db.relationship(
        "Post", backref=db.backref("parent", remote_side=[id]), lazy=True
    )
    attachments = db.relationship("Attachment", backref="post", lazy=True)
    flags = db.relationship("Flag", backref="post", lazy=True)
    versions = db.relationship(
        "PostVersion",
        backref="post",
        lazy=True,
        order_by="PostVersion.timestamp.desc()",
    )


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)


class Flag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.String(255))
    resolved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class PostVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)


class ModNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    mod_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
