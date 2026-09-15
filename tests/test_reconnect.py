import time
import serial
from sentinel.acquisition.simulator import Simulator
from sentinel.runner import run


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
