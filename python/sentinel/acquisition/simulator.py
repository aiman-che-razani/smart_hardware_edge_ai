"""Synthetic tank/environmental fixture. Never represents measured tank behavior."""
import math
import random

from .protocol import Sample, Kind, CONFIG, ACK, COMMAND, encode, Parser

# Mirrors the calibration defaults in pipeline.py, so a simulated run's raw
# fields convert back to plausible physical values.
DISTANCE_EMPTY_MM, DISTANCE_FULL_MM = 1000, 50
WATER_DRY_RAW, WATER_WET_RAW = 200, 800


def _level_fraction(t, condition):
    """0 = empty tank, 1 = full tank."""
    if condition == "LOW_WATER":
        return 0.06
    if condition == "OVERFLOW":
        return 0.98
    if condition == "RAPID_DRAIN":
        return max(0.05, 0.75 - 0.02 * t)  # ~1.2%/s unexplained drain: a leak proxy.
    if condition == "SENSOR_MISMATCH":
        return 0.5
    return 0.55 + 0.05 * math.sin(2 * math.pi * t / 120)  # NORMAL / ENVIRONMENTAL_ANOMALY.


class Simulator:
    def __init__(self, fs=1, condition="NORMAL", seed=42, drop_every=0, corrupt_every=0):
        self.fs, self.condition = fs, condition
        self.rng = random.Random(seed)
        self.boot = self.rng.randrange(1, 2**32)
        self.sequence = 0
        self.drop_every, self.corrupt_every = drop_every, corrupt_every
        self.alarm = 3
        self.streaming = True
        self.command_parser = Parser()

    def config(self):
        report_ms = round(1000 / self.fs)
        return encode(Kind.STATUS, CONFIG.pack(self.boot, report_ms, 150, 2000))

    def read(self, count=1):
        output = bytearray()
        if not self.streaming:
            return b""
        for _ in range(count):
            i = self.sequence
            t = i / self.fs
            condition = self.condition
            if condition == "CYCLE":
                block = int(t / 8) % 3
                local_t = t % 8
                condition = "NORMAL" if block != 1 else "RAPID_DRAIN"
            else:
                local_t = t

            fraction = _level_fraction(local_t, condition)
            noise = self.rng.gauss(0, 0.01)
            distance_mm = round(DISTANCE_EMPTY_MM - (fraction + noise) *
                                 (DISTANCE_EMPTY_MM - DISTANCE_FULL_MM))
            distance_mm = max(0, min(65535, distance_mm))

            water_fraction = fraction if condition != "SENSOR_MISMATCH" else max(0, fraction - 0.25)
            water_level_raw = round(WATER_DRY_RAW + (water_fraction + noise) *
                                     (WATER_WET_RAW - WATER_DRY_RAW))
            water_level_raw = max(0, min(1023, water_level_raw))

            if condition == "ENVIRONMENTAL_ANOMALY":
                ambient_temp_c_ds = round((40 + self.rng.gauss(0, 1)) * 10)
                ambient_humidity_ds = round((85 + self.rng.gauss(0, 2)) * 10)
                thermistor_raw = 380
                light_raw = 900
            else:
                ambient_temp_c_ds = round((24 + self.rng.gauss(0, 0.3)) * 10)
                ambient_humidity_ds = round((50 + self.rng.gauss(0, 1)) * 10)
                thermistor_raw = 512
                light_raw = 512

            sample = Sample(self.boot, i & 0xFFFFFFFF, round(t * 1000) & 0xFFFFFFFF,
                             distance_mm, round(t * 1000) % 150,
                             water_level_raw, thermistor_raw, light_raw,
                             ambient_temp_c_ds, ambient_humidity_ds, round(t * 1000) % 2000,
                             3)  # flags: DISTANCE_VALID | AMBIENT_VALID
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
