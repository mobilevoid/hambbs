from openbbs import create_app, db
from openbbs.models import User, Forum, Post, Flag, ModNote
from openbbs.views import generate_action_token
import pytest


@pytest.fixture
def app_ctx(tmp_path):
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{tmp_path / "test.db"}'
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app_ctx):
    return app_ctx.test_client()


def create_user(username, is_mod=False):
    user = User(username=username, password="pw", is_moderator=is_mod)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(User.query.filter_by(username=username).first().id)


def test_delete_flagged_post(app_ctx, client):
    mod = create_user("mod", is_mod=True)
    user = create_user("bob")
    forum = Forum(name="f1")
    db.session.add(forum)
    db.session.commit()
    post = Post(title="t", body="b", author=user, forum=forum)
    db.session.add(post)
    db.session.commit()
    flag = Flag(post=post, reporter=user, reason="spam")
    db.session.add(flag)
    db.session.commit()
    login(client, "mod")
    token = generate_action_token(post.id, mod.id)
    resp = client.post(
        f"/flag/{flag.id}/delete", data={"token": token, "reason": "bad"}
    )
    assert resp.status_code == 302
    assert Post.query.get(post.id) is None
    note = ModNote.query.filter_by(post_id=post.id).first()
    assert note is not None and "bad" in note.text
