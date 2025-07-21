import serial

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

class SimulatedVaraHF(RadioInterface):
    """Placeholder for VaraHF protocol support."""
    pass
