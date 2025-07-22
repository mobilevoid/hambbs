from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from pathlib import Path
from cryptography.fernet import Fernet

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
    app.config['ENCRYPTION_KEY_PATH'] = str(Path('encryption.key'))

    def load_enc_key(path: Path) -> bytes:
        if path.exists():
            return path.read_bytes()
        key = Fernet.generate_key()
        path.write_bytes(key)
        return key

    app.config['ENCRYPTION_KEY'] = load_enc_key(Path(app.config['ENCRYPTION_KEY_PATH']))

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User, Post, Forum, Attachment

    with app.app_context():
        Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
        db.create_all()
        init_db(DB_NAME)

    from .auth import auth_bp
    from .views import main_bp, generate_action_token
    from .forums import forums_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(forums_bp)
    from .sync_api import sync_bp
    app.register_blueprint(sync_bp)
    from .api import api_bp
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_action_token():
        from flask_login import current_user

        def action_token(post_id: int) -> str:
            if not current_user.is_authenticated:
                return ""
            return generate_action_token(post_id, current_user.id)

        return {"action_token": action_token}

    return app
