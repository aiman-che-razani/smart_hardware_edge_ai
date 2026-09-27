import time
import serial
from sentinel.acquisition.simulator import Simulator
from sentinel.runner import run
import pytest
from sentinel.storage.database import audit, connect
from sentinel.storage.queries import measurements


def test_serial_owner_recovers_and_restarts_stream(tmp_path, monkeypatch):
    connections=[]

    class Connection:
        def __init__(self,*args,**kwargs):
            self.device=Simulator(seed=len(connections)+90)
            self.pending=self.device.config()
            self.reads=0
            connections.append(self)
        def __enter__(self): return self
        def __exit__(self,*args): pass
        @property
        def in_waiting(self): return 2048
        def write(self,data):
            self.pending+=self.device.write(data)
            return len(data)
        def read(self,count):
            time.sleep(0.002)
            self.reads+=1
            if len(connections)==1 and self.reads==3:
                raise serial.SerialException('injected cable loss')
            self.pending+=self.device.read(40)
            data,self.pending=self.pending[:count],self.pending[count:]
            return data

    monkeypatch.setattr('sentinel.runner.serial.Serial',Connection)
    result=run(tmp_path,1.2,'NORMAL',port='FAKE-TEST-PORT')
    assert result['reconnections']>=2
    assert result['resets']>=1
    assert result['samples']>0
    assert not result['ack_errors']


class _Port:
    """Mock serial port. `script(port)` may change the device or raise; None means a silent device."""
    connections = []

    def __init__(self, factory, script=None):
        self.device = factory()
        self.pending = self.device.config()
        self.reads = 0
        self.script = script

    def __enter__(self): return self
    def __exit__(self, *args): pass

    @property
    def in_waiting(self): return 2048

    def write(self, data):
        self.pending += self.device.write(data)
        return len(data)

    def read(self, count):
        time.sleep(0.002)
        self.reads += 1
        if self.script:
            self.script(self)
        self.pending += self.device.read(2)
        data, self.pending = self.pending[:count], self.pending[count:]
        return data


def test_device_reporting_a_different_rate_is_refused_and_the_run_marked_failed(tmp_path, monkeypatch):
    monkeypatch.setattr("sentinel.runner.serial.Serial", lambda *a, **k: _Port(lambda: Simulator(fs=2)))
    with pytest.raises(ValueError, match="configuration mismatch"):
        run(tmp_path, 2, "NORMAL", port="FAKE-TEST-PORT")
    with connect(tmp_path) as db:
        assert db.execute("SELECT status FROM experiment_run").fetchone()[0] == "FAILED"
    assert audit(tmp_path)["unfinished_runs"] == []


def test_boot_change_on_a_live_stream_counts_a_reset_and_keeps_both_boots_apart(tmp_path, monkeypatch):
    def reboot(port):
        if port.reads == 20:
            port.device = Simulator(seed=7)
            port.pending += port.device.config()
    monkeypatch.setattr("sentinel.runner.serial.Serial", lambda *a, **k: _Port(lambda: Simulator(seed=1), reboot))
    result = run(tmp_path, 1.0, "NORMAL", port="FAKE-TEST-PORT")
    assert result["reconnections"] == 1 and result["resets"] >= 1
    assert len({row["boot"] for row in measurements(tmp_path, limit=3200)}) == 2
    assert not result["ack_errors"] and result["acquisition_status"] == "COMPLETE"


def test_silent_device_is_never_configured_and_its_commands_time_out(tmp_path, monkeypatch):
    class Silent:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        in_waiting = 0
        def write(self, data): return len(data)
        def read(self, count):
            time.sleep(0.005)
            return b""
    monkeypatch.setattr("sentinel.runner.serial.Serial", Silent)
    result = run(tmp_path, 2.0, "NORMAL", port="FAKE-TEST-PORT")
    assert result["samples"] == 0 and result["state"] == "UNKNOWN"
    assert result["command_failures"] >= 1 and result["acquisition_status"] == "COMPLETE"
