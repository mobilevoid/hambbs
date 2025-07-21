from radio import fec_encode, fec_decode, add_crc, verify_crc, interleave, deinterleave


def test_fec_round_trip():
    data = b"hello world"
    encoded = fec_encode(data)
    decoded = fec_decode(encoded)
    assert decoded == data


def test_crc_round_trip():
    data = b"abc123"
    framed = add_crc(data)
    assert verify_crc(framed) == data


def test_interleave_round_trip():
    data = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    inter = interleave(data, 4)
    deinter = deinterleave(inter, 4)
    assert deinter == data
