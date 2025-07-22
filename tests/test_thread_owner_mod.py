from openbbs import create_app, db
from openbbs.models import User, Forum, Post
from openbbs.views import generate_action_token, verify_owner_token, generate_owner_token
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


def test_thread_owner_token(app_ctx):
    owner = create_user('owner')
    forum = Forum(name='f1')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='t', body='b', author=owner, forum=forum)
    db.session.add(post)
    db.session.flush()
    post.owner_token = generate_owner_token(post.id, owner.id)
    db.session.commit()
    assert verify_owner_token(post)


def test_owner_can_make_mod(app_ctx, client):
    owner = create_user('alice')
    other = create_user('bob')
    forum = Forum(name='f2')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='topic', body='x', author=owner, forum=forum)
    db.session.add(post)
    db.session.flush()
    post.owner_token = generate_owner_token(post.id, owner.id)
    db.session.commit()
    assert verify_owner_token(post)
    login(client, 'alice')
    token = generate_action_token(other.id, owner.id)
    resp = client.post(f'/user/{other.id}/toggle_mod', data={'token': token, 'thread_id': post.id})
    assert resp.status_code == 302
    assert User.query.get(other.id).is_moderator


def test_non_owner_cannot_make_mod(app_ctx, client):
    owner = create_user('owner2')
    other = create_user('charlie')
    outsider = create_user('eve')
    forum = Forum(name='f3')
    db.session.add(forum)
    db.session.commit()
    post = Post(title='topic2', body='x', author=owner, forum=forum)
    db.session.add(post)
    db.session.flush()
    post.owner_token = generate_owner_token(post.id, owner.id)
    db.session.commit()
    login(client, 'eve')
    token = generate_action_token(other.id, outsider.id)
    resp = client.post(f'/user/{other.id}/toggle_mod', data={'token': token, 'thread_id': post.id})
    assert resp.status_code == 302
    assert not User.query.get(other.id).is_moderator

