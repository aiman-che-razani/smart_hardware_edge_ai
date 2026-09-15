import dataclasses
import struct
import pytest
from sentinel.acquisition.protocol import *
from sentinel.acquisition.commands import Commands
from sentinel.acquisition.csv_protocol import CSVParser
from sentinel.acquisition.simulator import Simulator


def sample(**kwargs):
    return dataclasses.replace(Sample(1, 1, 1250, -1, 2, 256, 1200, 480, 0, 0, 7), **kwargs)


def test_crc_reference_and_data_layout():
    assert crc16(b"123456789") == 0x29B1
    assert DATA.size == 27
    frame = sample().encode()
    assert len(frame) == 34
    assert Sample.decode(Parser().feed(frame)[0][1]) == sample()


@pytest.mark.parametrize("split", range(35))
def test_every_fragment_boundary(split):
    parser = Parser()
    frame = sample().encode()
    output = parser.feed(frame[:split]) + parser.feed(frame[split:])
    assert output == [(Kind.DATA, DATA.pack(*sample().__dict__.values()))]


def test_corruption_unknown_oversized_and_timeout_recovery():
    p = Parser()
    frame = sample().encode()
    bad = frame[:-1]+bytes([frame[-1]^1])
    assert len(p.feed(b"noise"+bad+encode(99,b"x")+b"\xa5\x5a\x01\x01\xff"+frame)) == 1
    assert p.errors >= 3
    p.feed(frame[:8],now=1)
    assert len(p.feed(frame,now=2)) == 1
    p.feed(b"x"*100000)
    assert len(p.buffer) <= 47


def test_continuity_wrap_reset_gap_duplicate():
    c = Continuity()
    assert c.accept(sample(sequence=0xFFFFFFFF,timestamp_us=0xFFFFFF00)) == (True,True)
    assert c.accept(sample(sequence=0,timestamp_us=994)) == (True,False)
    assert c.accept(sample(sequence=2,timestamp_us=3494)) == (True,True)
    assert c.gaps == 1
    assert c.accept(sample(sequence=2,timestamp_us=3494))[0] is False
    assert c.accept(sample(boot=2))[1]
    assert c.resets == 1


def test_commands_retry_idempotency_wrong_ack():
    commands, device = Commands(timeout=1,attempts=2), Simulator()
    frame = commands.begin(Kind.SET_ALARM,2,now=0)
    response = device.write(frame)
    assert device.alarm == 2
    assert commands.receive(ACK.pack(999,Kind.SET_ALARM,0)) is None
    assert commands.retry(now=1) == frame
    assert device.write(frame) == response
    assert commands.receive(Parser().feed(response)[0][1]) == (Kind.SET_ALARM,2,0)
    commands.begin(Kind.PING,now=0)
    commands.retry(now=1); commands.retry(now=2)
    assert commands.failures == 1


def test_csv_recovers_after_long_line_and_bad_integer():
    p = CSVParser()
    line = "D,"+",".join(str(v) for v in sample().__dict__.values())+"\n"
    assert p.feed(b"X\n"+b"q"*200+b"\n"+line.encode()) == [sample()]
    assert p.errors == 2
