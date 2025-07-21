import pytest
from radio import kiss_encode, kiss_decode


def test_kiss_round_trip():
    payload = b"\xc0hello\xdbtest"
    frame = kiss_encode(payload)
    assert frame.startswith(b"\xc0")
    decoded = kiss_decode(frame)
    assert decoded == payload
