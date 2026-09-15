"""Little-endian framed protocol with CRC-16/CCITT-FALSE."""
from dataclasses import dataclass
from enum import IntEnum
import struct
import time

MAGIC = b"\xa5\x5a"
VERSION = 1
MAX_PAYLOAD = 40
DATA = struct.Struct("<IIIhhhh hHHB")
CONFIG = struct.Struct("<IHHH")
ACK = struct.Struct("<HBB")
COMMAND = struct.Struct("<HB")
ACC_VALID, CURRENT_VALID, TEMP_VALID, OVERRUN = 1, 2, 4, 8


class Kind(IntEnum):
    DATA = 1
    STATUS = 2
    ACK = 3
    ERROR = 4
    SET_ALARM = 16
    CLEAR_ALARM = 17
    START_STREAM = 18
    STOP_STREAM = 19
    PING = 20
    GET_CONFIG = 21


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode(kind, payload):
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload exceeds protocol limit")
    body = bytes((VERSION, int(kind), len(payload))) + payload
    return MAGIC + body + struct.pack("<H", crc16(body))


class Parser:
    def __init__(self, timeout=0.5):
        self.buffer = bytearray()
        self.errors = 0
        self.last_byte = None
        self.timeout = timeout

    def feed(self, chunk, now=None):
        now = time.monotonic() if now is None else now
        if self.buffer and self.last_byte is not None and now - self.last_byte > self.timeout:
            self.buffer.clear()
            self.errors += 1
        if chunk:
            self.last_byte = now
        frames = []
        for byte in chunk:
            self.buffer.append(byte)
            while len(self.buffer) >= 2:
                if self.buffer[:2] != MAGIC:
                    del self.buffer[0]
                    continue
                if len(self.buffer) < 5:
                    break
                version, kind, length = self.buffer[2:5]
                if version != VERSION or length > MAX_PAYLOAD:
                    self.errors += 1
                    del self.buffer[0]
                    continue
                size = length + 7
                if len(self.buffer) < size:
                    break
                frame = bytes(self.buffer[:size])
                if crc16(frame[2:-2]) != struct.unpack("<H", frame[-2:])[0]:
                    self.errors += 1
                    del self.buffer[0]
                    continue
                del self.buffer[:size]
                if kind not in Kind._value2member_map_:
                    self.errors += 1
                    continue
                frames.append((Kind(kind), frame[5:-2]))
        return frames


@dataclass(frozen=True)
class Sample:
    boot: int
    sequence: int
    timestamp_us: int
    ax: int
    ay: int
    az: int
    shunt_raw: int
    temp_raw: int
    current_age_ms: int
    temp_age_ms: int
    flags: int

    @classmethod
    def decode(cls, payload):
        if len(payload) != DATA.size:
            raise ValueError("wrong DATA length")
        return cls(*DATA.unpack(payload))

    def encode(self):
        return encode(Kind.DATA, DATA.pack(*self.__dict__.values()))


class Continuity:
    def __init__(self):
        self.previous = None
        self.gaps = self.resets = self.duplicates = self.out_of_order = 0
        self.elapsed_us = 0

    def accept(self, sample):
        p = self.previous
        if p is None or sample.boot != p.boot:
            self.resets += int(p is not None)
            self.previous = sample
            self.elapsed_us = 0
            return True, True
        delta = (sample.sequence - p.sequence) & 0xFFFFFFFF
        if delta == 0:
            self.duplicates += 1
            return False, False
        if delta >= 0x80000000:
            self.out_of_order += 1
            return False, False
        dt = (sample.timestamp_us - p.timestamp_us) & 0xFFFFFFFF
        if dt >= 0x80000000:
            self.out_of_order += 1
            return False, False
        self.gaps += delta - 1
        self.elapsed_us += dt
        self.previous = sample
        return True, delta != 1
