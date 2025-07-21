from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


class KeyCache:
    """Simple on-disk cache of public keys with version counters."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._cache: Dict[str, Dict[str, str | int]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
        except Exception:
            return
        self._cache = {
            k: {"version": v["version"], "key": v["key"]} for k, v in data.items()
        }

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._cache))
        tmp.replace(self.path)

    def get(self, user: str) -> Optional[Ed25519PublicKey]:
        info = self._cache.get(user)
        if not info:
            return None
        key_bytes = bytes.fromhex(info["key"])
        return Ed25519PublicKey.from_public_bytes(key_bytes)

    def update(self, user: str, version: int, key: Ed25519PublicKey) -> None:
        hex_key = key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()
        cached = self._cache.get(user)
        if cached and cached["version"] >= version:
            return
        self._cache[user] = {"version": version, "key": hex_key}
        self._save()


def sign_checkpoint(private_key: Ed25519PrivateKey, root_hash: bytes) -> bytes:
    """Return a signature over *root_hash* using *private_key*."""
    return private_key.sign(root_hash)


def verify_checkpoint(
    public_key: Ed25519PublicKey, root_hash: bytes, signature: bytes
) -> bool:
    """Return ``True`` if *signature* is valid for *root_hash*."""
    try:
        public_key.verify(signature, root_hash)
        return True
    except Exception:
        return False
