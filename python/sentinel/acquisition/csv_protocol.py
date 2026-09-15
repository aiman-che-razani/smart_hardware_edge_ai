import struct
from .protocol import Sample, DATA


class CSVParser:
    def __init__(self):
        self.buffer = bytearray()
        self.discard = False
        self.errors = 0

    def feed(self, chunk):
        samples = []
        for byte in chunk:
            if byte == 10:
                if not self.discard:
                    try:
                        parts = self.buffer.decode("ascii").strip().split(",")
                        if len(parts) != 12 or parts[0] != "D":
                            raise ValueError("invalid CSV")
                        samples.append(Sample.decode(DATA.pack(*(int(x) for x in parts[1:]))))
                    except (ValueError, UnicodeError, OverflowError, struct.error):
                        self.errors += 1
                self.buffer.clear()
                self.discard = False
            elif not self.discard:
                self.buffer.append(byte)
                if len(self.buffer) > 160:
                    self.errors += 1
                    self.buffer.clear()
                    self.discard = True
        return samples
