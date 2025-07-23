from flask import Flask
from openbbs.views import encrypt_attachment, decrypt_attachment


def test_encrypt_decrypt_roundtrip():
    app = Flask(__name__)
    with app.app_context():
        data = b"secret data"
        comp = encrypt_attachment(data)
        dec = decrypt_attachment(comp)
        assert dec == data

