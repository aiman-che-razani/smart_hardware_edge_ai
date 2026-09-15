import argparse
import json
import logging
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="SentinelDAQ: physical or explicitly simulated condition monitoring")
    parser.add_argument("--data", default="data", help="SQLite/Parquet output directory")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("simulate", "acquire"):
        sub = commands.add_parser(name)
        sub.add_argument("--seconds", type=float, default=24)
        sub.add_argument("--condition", default="CYCLE" if name == "simulate" else "NORMAL")
        sub.add_argument("--fs", type=int, choices=[100,800], default=800)
        sub.add_argument("--model", type=Path)
        sub.add_argument("--window-seconds", type=float, default=1.0)
        sub.add_argument("--overlap", type=float, default=0.5)
        sub.add_argument("--warning", type=float, default=0.5)
        sub.add_argument("--fault", type=float, default=0.8)
        sub.add_argument("--recovery", type=float, default=0.3)
        sub.add_argument("--persistence", type=int, default=3)
        sub.add_argument("--recovery-windows", type=int, default=5)
        sub.add_argument("--machine", default="rig-1")
        sub.add_argument("--notes", default="")
        sub.add_argument("--metadata-json", type=Path)
        if name == "simulate":
            sub.add_argument("--realtime", action="store_true")
            sub.add_argument("--seed", type=int, default=42)
            sub.add_argument("--drop-every", type=int, default=0)
            sub.add_argument("--corrupt-every", type=int, default=0)
        else:
            sub.add_argument("--port", required=True)
            sub.add_argument("--baud", type=int, default=500000)
    sub = commands.add_parser("dataset", help="Generate separate labelled SYNTHETIC runs for testing")
    sub.add_argument("--runs", type=int, default=5)
    sub.add_argument("--seconds", type=float, default=8)
    sub = commands.add_parser("train")
    sub.add_argument("--output", type=Path, required=True)
    sub.add_argument("--simulated", action="store_true")
    sub = commands.add_parser("evaluate")
    sub.add_argument("--model-dir", type=Path, required=True)
    for name, port in (("api",8000),("dashboard",8050)):
        sub = commands.add_parser(name)
        sub.add_argument("--port", type=int, default=port)
    commands.add_parser("audit")
    sub = commands.add_parser("profile")
    sub.add_argument("--output", type=Path, required=True)
    sub.add_argument("--model", type=Path)
    sub = commands.add_parser("analyze")
    sub.add_argument("--run-id")
    sub = commands.add_parser("report")
    sub.add_argument("--run-id")
    sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("benchmark")
    sub.add_argument("--seconds", type=float, default=60)
    sub = commands.add_parser("csv", help="Read-only live V0 debug display")
    sub.add_argument("--port", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = None
    if args.command in ("simulate", "acquire", "benchmark"):
        from sentinel.runner import run
        kwargs = vars(args).copy()
        kwargs.pop("command"); kwargs.pop("data")
        kwargs["duration"] = kwargs.pop("seconds")
        result = run(args.data, **kwargs)
    elif args.command == "dataset":
        from sentinel.runner import run
        if args.runs < 3 or args.seconds < 2:
            parser.error("dataset needs >=3 runs/class and >=2 seconds/run")
        result = []
        for condition in ("NORMAL", "IMBALANCE_LOW", "IMBALANCE_HIGH", "LOOSE_MOUNT"):
            for number in range(args.runs):
                result.append(run(args.data, args.seconds, condition, seed=1000+number+len(result)*7))
    elif args.command == "train":
        from sentinel.ml.train import train
        result = train(args.data, args.output, args.simulated)
    elif args.command == "evaluate":
        from sentinel.ml.train import evaluate
        result = evaluate(args.data, args.model_dir)
    elif args.command == "api":
        import uvicorn
        from sentinel.api.main import create_app
        uvicorn.run(create_app(args.data), host="127.0.0.1", port=args.port)
    elif args.command == "dashboard":
        from sentinel.dashboard import create_dashboard
        create_dashboard(args.data).run(host="127.0.0.1", port=args.port, debug=False)
    elif args.command == "audit":
        from sentinel.storage.database import audit
        result = audit(args.data)
    elif args.command == "analyze":
        from sentinel.benchmark import analyze
        result = analyze(args.data,args.run_id)
    elif args.command == "profile":
        from sentinel.profiling import profile
        result = profile(args.output,args.model)
    elif args.command == "report":
        from sentinel.report import export
        result = export(args.data,args.output,args.run_id)
    elif args.command == "csv":
        import serial
        from sentinel.acquisition.csv_protocol import CSVParser
        decoder = CSVParser()
        try:
            with serial.Serial(args.port,115200,timeout=0.2) as connection:
                while True:
                    for sample in decoder.feed(connection.read(512)):
                        print(sample)
        except KeyboardInterrupt:
            print(f"Stopped. Malformed lines: {decoder.errors}")
    if result is not None:
        print(json.dumps(result, indent=2))
