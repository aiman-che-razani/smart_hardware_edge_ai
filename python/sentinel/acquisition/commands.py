import time
from .protocol import COMMAND, ACK, Kind, encode

HOST_COMMANDS = frozenset((Kind.SET_ALARM, Kind.CLEAR_ALARM, Kind.START_STREAM, Kind.STOP_STREAM, Kind.PING, Kind.GET_CONFIG))
MAX_ALARM_STATE = 3  # mirrors the firmware's `value<=3` check


class Commands:
    """One in-flight command; retry exact bytes, match ACK ID and operation."""
    def __init__(self, timeout=0.5, attempts=3):
        self.timeout, self.attempts = timeout, attempts
        self.next_id = 0
        self.pending = None
        self.failures = 0
        self.last_ack = None

    def begin(self, kind, value=0, now=None):
        if self.pending:
            raise RuntimeError("command already pending")
        if kind not in HOST_COMMANDS:
            raise ValueError(f"not a host command: {kind}")
        if not 0 <= value <= (MAX_ALARM_STATE if kind == Kind.SET_ALARM else 255):
            raise ValueError("command value out of range")
        self.next_id = (self.next_id + 1) & 0xFFFF
        frame = encode(kind, COMMAND.pack(self.next_id, value))
        self.pending = [self.next_id, kind, value, frame, time.monotonic() if now is None else now, 1]
        return frame

    def receive(self, payload):
        if len(payload) != ACK.size or not self.pending:
            return None
        identity, kind, error = ACK.unpack(payload)
        if (identity, kind) != tuple(self.pending[:2]):
            return None
        result = (self.pending[1], self.pending[2], error)
        self.pending = None
        self.last_ack = result
        return result

    def retry(self, now=None):
        now = time.monotonic() if now is None else now
        if self.pending and now-self.pending[4] >= self.timeout:
            if self.pending[5] >= self.attempts:
                self.failures += 1
                self.pending = None
                return None
            self.pending[4] = now
            self.pending[5] += 1
            return self.pending[3]
        return None
