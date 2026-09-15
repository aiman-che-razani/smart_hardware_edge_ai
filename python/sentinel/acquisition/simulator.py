"""Synthetic rotating-signal fixture. Never represents measured machine behavior."""
import math
import random
import struct
from .protocol import Sample, Kind, CONFIG, ACK, COMMAND, encode, Parser


class Simulator:
    def __init__(self, fs=800, condition="NORMAL", seed=42, drop_every=0, corrupt_every=0):
        self.fs, self.condition = fs, condition
        self.rng = random.Random(seed)
        self.boot = self.rng.randrange(1, 2**32)
        self.sequence = 0
        self.drop_every, self.corrupt_every = drop_every, corrupt_every
        self.alarm = 3
        self.streaming = True
        self.command_parser = Parser()

    def config(self):
        return encode(Kind.STATUS, CONFIG.pack(self.boot, self.fs, 3900, 100))

    def read(self, count=80):
        output = bytearray()
        if not self.streaming:
            return b""
        for _ in range(count):
            i = self.sequence
            t = i / self.fs
            condition = self.condition
            if condition == "CYCLE":
                condition = "NORMAL" if int(t / 8) % 3 != 1 else "IMBALANCE_HIGH"
            amplitude = {"NORMAL": 0.025, "IMBALANCE_LOW": 0.12, "IMBALANCE_HIGH": 0.45,
                         "LOOSE_MOUNT": 0.18, "PARTIAL_OBSTRUCTION": 0.22,
                         "INCREASED_LOAD": 0.15, "SPEED_VARIATION": 0.08}.get(condition)
            if amplitude is None:
                raise ValueError("unknown synthetic condition")
            phase = 2 * math.pi * (30*t + (0.4*t*t if condition == "SPEED_VARIATION" else 0))
            x = amplitude * math.sin(phase) + self.rng.gauss(0, 0.005)
            if condition == "LOOSE_MOUNT" and i % 97 == 0:
                x += 0.9
            values = [round(x/0.0039), round(amplitude*0.5*math.sin(phase+0.8)/0.0039),
                      round((1+amplitude*0.3*math.sin(2*phase))/0.0039)]
            sample = Sample(self.boot, i & 0xFFFFFFFF, round(t*1e6) & 0xFFFFFFFF,
                            *values, 1200, 480, round(t*1000)%40, round(t*1000)%1000, 7)
            frame = sample.encode()
            self.sequence += 1
            if self.drop_every and self.sequence % self.drop_every == 0:
                continue
            if self.corrupt_every and self.sequence % self.corrupt_every == 0:
                frame = frame[:-1] + bytes([frame[-1] ^ 1])
            output.extend(frame)
        return bytes(output)

    def write(self, data):
        output = bytearray()
        for kind, payload in self.command_parser.feed(data):
            if len(payload) != COMMAND.size:
                continue
            command_id, value = COMMAND.unpack(payload)
            error = 0
            if kind == Kind.SET_ALARM and value <= 3:
                self.alarm = value
            elif kind == Kind.CLEAR_ALARM:
                self.alarm = 0
            elif kind == Kind.START_STREAM:
                self.streaming = True
            elif kind == Kind.STOP_STREAM:
                self.streaming = False
            elif kind not in (Kind.PING, Kind.GET_CONFIG):
                error = 1
            output.extend(encode(Kind.ACK, ACK.pack(command_id, kind, error)))
            if kind == Kind.GET_CONFIG:
                output.extend(self.config())
        return bytes(output)
