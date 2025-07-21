import serial
import socket

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

class SimulatedVaraHF(VaraHFClient):
    """Backward compatible alias for VaraHFClient."""
    pass
