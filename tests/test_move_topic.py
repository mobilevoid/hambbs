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


def test_move_topic(app_ctx, client):
    mod = create_user('mod', is_mod=True)
    forum1 = Forum(name='f1')
    forum2 = Forum(name='f2')
    db.session.add_all([forum1, forum2])
    db.session.commit()
    post = Post(title='t', body='b', author=mod, forum=forum1)
    db.session.add(post)
    db.session.commit()
    login(client, 'mod')
    token = generate_action_token(post.id, mod.id)
    resp = client.post(f'/post/{post.id}/move', data={'forum_id': forum2.id, 'token': token})
    assert resp.status_code == 302
    assert Post.query.get(post.id).forum_id == forum2.id
