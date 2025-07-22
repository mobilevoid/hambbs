from openbbs import create_app, db
from openbbs.models import User, Forum, Post
import pytest

@pytest.fixture
def app_ctx(tmp_path):
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path / "test.db"}'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app

@pytest.fixture
def client(app_ctx):
    return app_ctx.test_client()


def create_user(username, is_mod=False):
    user = User(username=username, password='pw', is_moderator=is_mod)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(User.query.filter_by(username=username).first().id)


def test_edit_post_updates_timestamp(app_ctx, client):
    user = create_user('alice')
    forum = Forum(name='f1')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='t', body='b', author=user, forum=forum)
    db.session.add(post)
    db.session.commit()
    login(client, 'alice')
    resp = client.post(f'/post/{post.id}/edit', data={'title': 't2', 'body': 'b2'})
    assert resp.status_code == 302
    updated = Post.query.get(post.id)
    assert updated.title == 't2'
    assert updated.edited_at is not None


def test_soft_delete_for_user(app_ctx, client):
    user = create_user('bob')
    forum = Forum(name='f2')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='t', body='b', author=user, forum=forum)
    db.session.add(post)
    db.session.commit()
    login(client, 'bob')
    resp = client.post(f'/post/{post.id}/delete')
    assert resp.status_code == 302
    assert Post.query.get(post.id).deleted


def test_hard_delete_for_moderator(app_ctx, client):
    mod = create_user('mod', is_mod=True)
    user = create_user('user')
    forum = Forum(name='f3')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='t', body='b', author=user, forum=forum)
    db.session.add(post)
    db.session.commit()
    login(client, 'mod')
    resp = client.post(f'/post/{post.id}/delete')
    assert resp.status_code == 302
    assert Post.query.get(post.id) is None

