from __future__ import annotations
import serial
import socket
import threading
import time
from typing import Iterable, List, Callable

import crcmod.predefined
from reedsolo import RSCodec

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD


class RadioInterface:
    """Simple radio interface using a serial COM port."""

    def __init__(self, port, baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def open(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def close(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    def send(self, data: bytes):
        if not self.ser:
            self.open()
        self.ser.write(data)

    def receive(self, size=1024) -> bytes:
        if not self.ser:
            self.open()
        return self.ser.read(size)

    def is_busy(self) -> bool:
        """Return True if the radio reports a busy channel."""
        if not self.ser:
            self.open()
        busy = False
        try:
            busy = bool(
                getattr(self.ser, "cts", False) or getattr(self.ser, "cd", False)
            )
        except Exception:
            pass
        return busy

    def negotiate_baud(self, rates: Iterable[int] = (57600, 38400, 19200, 9600)) -> int:
        """Attempt to open the serial port at the fastest working baud rate."""
        for rate in rates:
            try:
                with serial.Serial(self.port, rate, timeout=0.5) as test:
                    test.write(b"?")
                    resp = test.read(1)
                    if resp:
                        self.baudrate = rate
                        self.ser = serial.Serial(
                            self.port, self.baudrate, timeout=self.timeout
                        )
                        return rate
            except serial.SerialException:
                continue
        raise RuntimeError("no supported baud rate")

    def start_heartbeat(self, interval: float = 30.0):
        """Start a background thread sending periodic heartbeat frames."""
        if hasattr(self, "_hb_thread") and self._hb_thread.is_alive():
            return

        def _hb():
            while getattr(self, "_hb_running", False):
                try:
                    self.send(b"\x00")
                except Exception:
                    pass
                time.sleep(interval)

        self._hb_running = True
        self._hb_thread = threading.Thread(target=_hb, daemon=True)
        self._hb_thread.start()

    def stop_heartbeat(self):
        """Stop the background heartbeat."""
        self._hb_running = False
        if hasattr(self, "_hb_thread"):
            self._hb_thread.join(timeout=1)


def kiss_encode(payload: bytes) -> bytes:
    """Encode raw bytes into a KISS frame."""
    frame = bytearray([FEND, 0x00])  # port 0
    for b in payload:
        if b == FEND:
            frame.extend([FESC, TFEND])
        elif b == FESC:
            frame.extend([FESC, TFESC])
        else:
            frame.append(b)
    frame.append(FEND)
    return bytes(frame)


def kiss_decode(frame: bytes) -> bytes:
    """Decode a KISS frame into raw bytes."""
    if not frame or frame[0] != FEND:
        raise ValueError("Invalid KISS frame")
    payload = bytearray()
    esc = False
    for b in frame[2:]:
        if esc:
            if b == TFEND:
                payload.append(FEND)
            elif b == TFESC:
                payload.append(FESC)
            else:
                raise ValueError("Invalid escape sequence")
            esc = False
            continue
        if b == FESC:
            esc = True
            continue
        if b == FEND:
            break
        payload.append(b)
    return bytes(payload)


def kiss_decode_stream(stream: bytes) -> bytes:
    """Extract the first complete KISS frame from *stream*.

    Returns the decoded payload or ``b''`` if a complete frame has not yet
    been received. The provided buffer is not modified.
    """
    buf = bytearray()
    in_frame = False
    escape = False
    for b in stream:
        if not in_frame:
            if b == FEND:
                in_frame = True
                buf.clear()
            continue
        if escape:
            if b == TFEND:
                buf.append(FEND)
            elif b == TFESC:
                buf.append(FESC)
            else:
                buf.append(b)
            escape = False
            continue
        if b == FESC:
            escape = True
            continue
        if b == FEND:
            # drop port byte
            return bytes(buf[1:])
        buf.append(b)
    return b""


# ---- Error correction and framing utilities ----

rsc = RSCodec(10)
crc16 = crcmod.predefined.mkCrcFun("crc-16")


def fec_encode(data: bytes) -> bytes:
    """Encode *data* with Reed-Solomon FEC."""
    return bytes(rsc.encode(data))


def fec_decode(data: bytes) -> bytes:
    """Decode Reed-Solomon encoded *data*. Raises ``ValueError`` on failure."""
    decoded, _, _ = rsc.decode(data)
    return bytes(decoded)


def add_crc(data: bytes) -> bytes:
    """Append CRC-16 to *data*."""
    crc = crc16(data)
    return data + crc.to_bytes(2, "big")


def verify_crc(frame: bytes) -> bytes:
    """Return payload if CRC matches, else raise ``ValueError``."""
    if len(frame) < 2:
        raise ValueError("frame too short for CRC")
    data, chk = frame[:-2], frame[-2:]
    if crc16(data) != int.from_bytes(chk, "big"):
        raise ValueError("CRC mismatch")
    return data


def interleave(data: bytes, block: int = 4) -> bytes:
    """Simple block interleaver."""
    if block <= 1:
        return data
    pad = (-len(data)) % block
    padded = data + b"\x00" * pad
    rows = [padded[i : i + block] for i in range(0, len(padded), block)]
    out = bytearray()
    for i in range(block):
        for row in rows:
            out.append(row[i])
    return bytes(out)


def deinterleave(data: bytes, block: int = 4) -> bytes:
    """Reverse :func:`interleave`."""
    if block <= 1:
        return data
    rows = len(data) // block
    matrix = [bytearray(block) for _ in range(rows)]
    idx = 0
    for i in range(block):
        for j in range(rows):
            matrix[j][i] = data[idx]
            idx += 1
    out = b"".join(matrix)
    return out.rstrip(b"\x00")


def chunk_data(data: bytes, size: int = 256) -> List[bytes]:
    """Split *data* into MTU-sized chunks."""
    return [data[i : i + size] for i in range(0, len(data), size)]


class SlidingWindowARQ:
    """Very small sliding-window ARQ helper."""

    def __init__(self, tnc: KISSTnc, window: int = 4, timeout: float = 2.0):
        self.tnc = tnc
        self.window = window
        self.timeout = timeout
        self._seq = 0
        self._unacked: dict[int, bytes] = {}

    def send(self, payload: bytes) -> None:
        for chunk in chunk_data(payload):
            self._send_chunk(chunk)

    def _send_chunk(self, chunk: bytes) -> None:
        while len(self._unacked) >= self.window:
            self._wait_for_ack()
        seq = self._seq
        frame = bytes([seq])
        frame = fec_encode(frame + chunk)
        frame = add_crc(frame)
        self.tnc.send_packet(frame)
        self._unacked[seq] = frame
        self._seq = (self._seq + 1) % 256

    def _wait_for_ack(self) -> None:
        start = time.time()
        while time.time() - start < self.timeout:
            data = self.tnc.receive_packet()
            if not data:
                continue
            try:
                payload = verify_crc(data)
                payload = fec_decode(payload)
            except Exception:
                continue
            if payload.startswith(b"A"):
                ack = payload[1]
                self._unacked.pop(ack, None)
                return

    def receive(self) -> bytes:
        data = self.tnc.receive_packet()
        if not data:
            return b""
        try:
            payload = verify_crc(data)
            payload = fec_decode(payload)
        except Exception:
            return b""
        seq = payload[0]
        self.tnc.send_packet(add_crc(fec_encode(b"A" + bytes([seq]))))
        return payload[1:]


class VaraHFClient:
    """Basic TCP client for communicating with a VaraHF modem."""

    def __init__(self, host="localhost", port=8300, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def open(self):
        self.sock = socket.create_connection((self.host, self.port), self.timeout)

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, data: bytes):
        if not self.sock:
            self.open()
        self.sock.sendall(data)

    def receive(self, size=1024) -> bytes:
        if not self.sock:
            self.open()
        return self.sock.recv(size)


class KISSTnc:
    """Wrap a radio interface with KISS encoding/decoding."""

    def __init__(self, iface: RadioInterface):
        self.iface = iface

    def send_packet(self, data: bytes):
        self.iface.send(kiss_encode(data))

    def receive_packet(self, size=1024) -> bytes:
        buf = bytearray()
        while True:
            chunk = self.iface.receive(1)
            if not chunk:
                if buf:
                    break
                continue
            buf.append(chunk[0])
            if chunk[0] == FEND and len(buf) > 1:
                break
        return kiss_decode(bytes(buf))


class VaraKISS:
    """Serial-port wrapper for VARA in KISS mode."""

    def __init__(self, port: str, baud: int = 9600, timeout: float = 0.1):
        self.ser = serial.Serial(port, baud, timeout=timeout)
        self.rx_buffer = bytearray()
        self.lock = threading.Lock()

    def send(self, payload: bytes) -> None:
        frame = kiss_encode(payload)
        with self.lock:
            self.ser.write(frame)

    def receive(self) -> bytes:
        chunk = self.ser.read(4096)
        if chunk:
            self.rx_buffer += chunk
            data = kiss_decode_stream(self.rx_buffer)
            if data:
                end = self.rx_buffer.find(bytes([FEND]), 1)
                self.rx_buffer = self.rx_buffer[end + 1 :]
                return data
        return b""

    def close(self) -> None:
        self.ser.close()


class SimulatedVaraHF(VaraHFClient):
    """In-memory mock of :class:`VaraHFClient` for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize the mock client with optional VaraHF parameters."""
        super().__init__(*args, **kwargs)
        self._incoming: list[bytes] = []
        self.sent: list[bytes] = []

    def feed(self, data: bytes) -> None:
        """Provide data that will be returned by :meth:`receive`."""
        self._incoming.append(data)

    def open(self):
        """Simulated open -- no external resources are used."""
        self.sock = True  # sentinel so methods think we are connected

    def close(self):
        self.sock = None

    def send(self, data: bytes):
        if not self.sock:
            self.open()
        self.sent.append(data)

    def receive(self, size=1024) -> bytes:
        if not self.sock:
            self.open()
        if not self._incoming:
            return b""
        data = self._incoming.pop(0)
        if len(data) > size:
            self._incoming.insert(0, data[size:])
            data = data[:size]
        return data


def opportunistic_relay(
    queue: List[bytes], forward_fn: Callable[[bytes], None]
) -> None:
    """Forward queued frames to another peer if possible.

    This is a very small placeholder implementation. In a real system we would
    inspect link quality reports and only forward when the peer's path to the
    server is better than our own.
    """
    for frame in list(queue):
        try:
            forward_fn(frame)
            queue.remove(frame)
        except Exception:
            # if forwarding fails, leave the frame in the queue
            pass
