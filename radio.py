import serial
import socket
import threading

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
                self.rx_buffer = self.rx_buffer[end + 1:]
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
