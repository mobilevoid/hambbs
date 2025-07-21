from keycache import VersionedKeyCache


def test_keycache_update_and_get(tmp_path):
    path = tmp_path / "kc.json"
    kc = VersionedKeyCache(str(path))
    assert kc.update("abc", 1, "KEYDATA")
    assert kc.get("abc") == (1, "KEYDATA")
    # lower version should not replace
    assert not kc.update("abc", 1, "NEW")
    assert kc.get("abc") == (1, "KEYDATA")
    # higher version replaces
    assert kc.update("abc", 2, "NEW")
    assert kc.get("abc") == (2, "NEW")
