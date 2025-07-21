from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

@dataclass
class KeyEntry:
    fingerprint: str
    version: int
    key_data: str

class VersionedKeyCache:
    """Simple on-disk cache of keys identified by fingerprint and version."""
    def __init__(self, path: str = 'keycache.json'):
        self.path = Path(path)
        self._cache: dict[str, KeyEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            with open(self.path) as f:
                data = json.load(f)
            for fp, entry in data.items():
                self._cache[fp] = KeyEntry(**entry)

    def _save(self) -> None:
        with open(self.path, 'w') as f:
            json.dump({fp: asdict(e) for fp, e in self._cache.items()}, f)

    def get(self, fingerprint: str) -> Optional[tuple[int, str]]:
        entry = self._cache.get(fingerprint)
        if entry:
            return entry.version, entry.key_data
        return None

    def update(self, fingerprint: str, version: int, key_data: str) -> bool:
        entry = self._cache.get(fingerprint)
        if entry and entry.version >= version:
            return False
        self._cache[fingerprint] = KeyEntry(fingerprint, version, key_data)
        self._save()
        return True
