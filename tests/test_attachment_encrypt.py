from flask import Flask
from openbbs.views import encrypt_attachment, decrypt_attachment
from cryptography.fernet import Fernet


def test_encrypt_decrypt_roundtrip():
    app = Flask(__name__)
    app.config['ENCRYPTION_KEY'] = Fernet.generate_key()
    with app.app_context():
        data = b"secret data"
        enc = encrypt_attachment(data)
        dec = decrypt_attachment(enc)
        assert dec == data

