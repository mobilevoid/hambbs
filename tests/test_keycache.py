from pathlib import Path
from keycache import KeyCache, sign_checkpoint, verify_checkpoint
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def test_keycache_update_and_get(tmp_path: Path):
    cache_path = tmp_path / "keys.json"
    kc = KeyCache(cache_path)
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    kc.update("alice", 1, pub)
    loaded = kc.get("alice")
    assert loaded.public_bytes_raw() == pub.public_bytes_raw()
    kc.update("alice", 0, pub)  # lower version should be ignored
    assert kc.get("alice").public_bytes_raw() == pub.public_bytes_raw()


def test_checkpoint_sign_verify():
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    data = b"test-root"
    sig = sign_checkpoint(priv, data)
    assert verify_checkpoint(pub, data, sig)
    assert not verify_checkpoint(pub, data + b"x", sig)
