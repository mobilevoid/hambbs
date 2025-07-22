from openbbs import create_app, db
from openbbs.models import User, Forum, Post
from openbbs.views import generate_action_token
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
    token = generate_action_token(post.id, user.id)
    resp = client.post(f'/post/{post.id}/edit', data={'title': 't2', 'body': 'b2', 'token': token})
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
    token = generate_action_token(post.id, user.id)
    resp = client.post(f'/post/{post.id}/delete', data={'token': token})
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
    token = generate_action_token(post.id, mod.id)
    resp = client.post(f'/post/{post.id}/delete', data={'token': token})
    assert resp.status_code == 302
    assert Post.query.get(post.id) is None


def test_invalid_token_prevents_edit(app_ctx, client):
    user = create_user('carol')
    forum = Forum(name='f4')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='t', body='b', author=user, forum=forum)
    db.session.add(post)
    db.session.commit()
    login(client, 'carol')
    resp = client.post(f'/post/{post.id}/edit', data={'title': 'x', 'body': 'y', 'token': 'bad'})
    assert resp.status_code == 302
    assert Post.query.get(post.id).title == 't'


def test_invalid_token_prevents_delete(app_ctx, client):
    user = create_user('dave')
    forum = Forum(name='f5')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='t', body='b', author=user, forum=forum)
    db.session.add(post)
    db.session.commit()
    login(client, 'dave')
    resp = client.post(f'/post/{post.id}/delete', data={'token': 'bad'})
    assert resp.status_code == 302
    assert not Post.query.get(post.id).deleted

