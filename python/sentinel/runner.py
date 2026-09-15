import json
import logging
from pathlib import Path
import queue
import threading
import time
import serial
from sentinel.acquisition.protocol import Parser, Sample, Kind, CONFIG
from sentinel.acquisition.commands import Commands
from sentinel.acquisition.simulator import Simulator
from sentinel.pipeline import Pipeline
from sentinel.storage.database import Store
from sentinel.storage.status import publish

LOG = logging.getLogger(__name__)
ALARM_VALUES = {"NORMAL": 0, "WARNING": 1, "FAULT": 2, "UNKNOWN": 3}


def run(root, duration=24, condition="CYCLE", port=None, fs=800, baud=500000,
        realtime=False, seed=42, drop_every=0, corrupt_every=0, model=None,
        window_seconds=1.0, overlap=0.5, warning=0.5, fault=0.8, recovery=0.3,
        persistence=3, recovery_windows=5, machine="rig-1", notes="", metadata_json=None):
    if duration <= 0 or fs not in (100, 800):
        raise ValueError("duration must be positive; supported sampling rates are 100/800 Hz")
    simulated = port is None
    operator_metadata = json.loads(Path(metadata_json).read_text()) if metadata_json else {}
    if not isinstance(operator_metadata, dict):
        raise ValueError("metadata JSON must be an object")
    store = Store(root)
    run_id = store.start(condition, fs, simulated, {"protocol": 1, "firmware": "0.1.0",
        "source": "SIMULATED" if simulated else "PHYSICAL", "seed": seed if simulated else None,
        "baud": baud, "acceleration_g_per_lsb": 0.0039, "shunt_ohms": 0.1,
        "window": {"seconds":window_seconds,"overlap":overlap},
        "operator_notes":notes,"operator_metadata":operator_metadata}, machine=machine)
    try:
        pipeline = Pipeline(store, fs, model, simulated, overlap, window_seconds,
            {"warning":warning,"fault":fault,"recovery":recovery,
             "persistence":persistence,"recovery_windows":recovery_windows})
    except Exception:
        store.close("FAILED")
        raise
    parser, commands = Parser(), Commands()
    stop = threading.Event()
    incoming, outgoing = queue.Queue(maxsize=128), queue.Queue(maxsize=16)
    counters = {"queue_drops": 0, "reconnections": 0, "ack_errors": 0, "status_publish_skips": 0}
    device = Simulator(fs, condition, seed, drop_every, corrupt_every) if simulated else None

    def serial_worker():
        delay = 0.25
        while not stop.is_set():
            try:
                with serial.Serial(port, baud, timeout=0.1, write_timeout=0.2) as connection:
                    counters["reconnections"] += 1
                    while not outgoing.empty():
                        try:
                            outgoing.get_nowait()
                        except queue.Empty:
                            break
                    incoming.put((None, time.time_ns()), timeout=0.5)
                    delay = 0.25
                    while not stop.is_set():
                        try:
                            connection.write(outgoing.get_nowait())
                        except queue.Empty:
                            pass
                        data = connection.read(min(max(connection.in_waiting, 1), 2048))
                        if data:
                            try:
                                incoming.put_nowait((data, time.time_ns()))
                            except queue.Full:
                                counters["queue_drops"] += 1
            except (serial.SerialException, OSError, queue.Full) as error:
                LOG.warning("serial unavailable: %s", error)
                stop.wait(delay)
                delay = min(5, delay*2)

    worker = None
    if not simulated:
        worker = threading.Thread(target=serial_worker, name="serial-owner", daemon=True)
        worker.start()
    pending_simulated = device.config() if simulated else b""
    configured = False
    stream_started = simulated
    configured_boot = None
    alarm_ack = None
    last_rx = time.monotonic()
    last_data = last_rx
    heartbeat = last_rx
    last_publish = last_rx
    started = last_rx
    cpu_started = time.process_time()
    status = "COMPLETE"

    def send(frame):
        nonlocal pending_simulated
        if simulated:
            pending_simulated += device.write(frame)
        else:
            try:
                outgoing.put_nowait(frame)
            except queue.Full:
                counters["queue_drops"] += 1

    try:
        while (device.sequence < duration*fs if simulated else time.monotonic()-started < duration):
            now = time.monotonic()
            if simulated:
                chunk = pending_simulated + device.read(min(80, max(1, int(duration*fs-device.sequence))))
                pending_simulated = b""
                host_ns = time.time_ns()
            else:
                try:
                    chunk, host_ns = incoming.get(timeout=0.1)
                except queue.Empty:
                    chunk, host_ns = b"", time.time_ns()
                if chunk is None:
                    pipeline.disconnect()
                    parser = Parser()
                    commands.pending = None
                    configured = False
                    stream_started = False
                    alarm_ack = None
                    chunk = b""
            for kind, payload in parser.feed(chunk):
                last_rx = now
                if kind == Kind.STATUS:
                    if len(payload) != CONFIG.size:
                        parser.errors += 1
                        continue
                    boot, rate, scale_ug, shunt_milliohm = CONFIG.unpack(payload)
                    if rate != fs or scale_ug == 0 or shunt_milliohm == 0:
                        raise ValueError("device configuration mismatch; set correct --fs and check sensor calibration")
                    if configured_boot is not None and boot != configured_boot:
                        pipeline.continuity.resets += 1
                        pipeline.disconnect()
                        alarm_ack = None
                        stream_started = False
                        commands.pending = None
                    configured_boot = boot
                    pipeline.scale, pipeline.shunt_ohms = scale_ug/1e6, shunt_milliohm/1000
                    configured = True
                elif kind == Kind.ACK:
                    result = commands.receive(payload)
                    if result:
                        command, value, error = result
                        counters["ack_errors"] += int(error != 0)
                        if not error and command in (Kind.SET_ALARM, Kind.CLEAR_ALARM):
                            alarm_ack = value
                            if value == ALARM_VALUES[pipeline.state.state]:
                                store.alarm_ack(next(k for k, v in ALARM_VALUES.items() if v == value))
                        if not error and command == Kind.START_STREAM:
                            stream_started = True
                elif kind == Kind.DATA and configured:
                    try:
                        sample = Sample.decode(payload)
                    except ValueError:
                        parser.errors += 1
                        continue
                    if sample.boot != configured_boot:
                        configured = False
                        pipeline.disconnect()
                        continue
                    pipeline.accept(sample, host_ns)
                    last_data = now
            if now-last_data > 2 and pipeline.state.state != "UNKNOWN":
                pipeline.disconnect()
                alarm_ack = None
            if now-last_rx > 2:
                pipeline.disconnect()
                configured = False
                stream_started = False
                alarm_ack = None
            retry = commands.retry(now)
            if retry:
                send(retry)
            desired = ALARM_VALUES[pipeline.state.state]
            if not commands.pending:
                if not configured:
                    send(commands.begin(Kind.GET_CONFIG, now=now))
                elif not stream_started:
                    send(commands.begin(Kind.START_STREAM, now=now))
                elif alarm_ack != desired:
                    send(commands.begin(Kind.SET_ALARM, desired, now))
                elif now-heartbeat > 1:
                    send(commands.begin(Kind.PING, now=now))
                    heartbeat = now
            if realtime and simulated:
                stop.wait(max(0, started+device.sequence/fs-time.monotonic()))
            if time.monotonic()-last_publish > 0.2:
                summary = dict(pipeline.summary(), **counters, parser_errors=parser.errors,
                               run_id=run_id, simulated=simulated, updated_at=time.time())
                if not publish(root,summary):
                    counters["status_publish_skips"] += 1
                last_publish = time.monotonic()
    except KeyboardInterrupt:
        status = "INTERRUPTED"
    except Exception:
        status = "FAILED"
        raise
    finally:
        stop.set()
        if worker:
            worker.join(timeout=2)
        summary = dict(pipeline.summary(), **counters, parser_errors=parser.errors,
                       command_failures=commands.failures, simulated=simulated, run_id=run_id,
                       elapsed_wall_s=time.monotonic()-started, updated_at=time.time(), acquisition_status=status)
        summary["process_cpu_s"] = time.process_time()-cpu_started
        store.close(status)
        if not publish(root,summary):
            counters["status_publish_skips"] += 1
            summary["status_publish_skips"] = counters["status_publish_skips"]
        (Path(root)/f"{run_id}-summary.json").write_text(json.dumps(summary, indent=2))
    return summary
