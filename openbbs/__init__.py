from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from pathlib import Path

from db import init_db

# Database instance
DB_NAME = 'openbbs.db'
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'change-this-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = str(Path('uploads'))

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User, Post, Forum, Attachment

    with app.app_context():
        Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
        db.create_all()
        init_db(DB_NAME)

    from .auth import auth_bp
    from .views import main_bp
    from .forums import forums_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(forums_bp)
    from .sync_api import sync_bp
    app.register_blueprint(sync_bp)

    return app
