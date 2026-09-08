from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

from typing import Optional, Tuple

from flask import Flask, Response, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import Database
from engine import Engine
from rover_client import RoverClient
from rover_sense import explain_ir
from serial_reader import SerialReader, resolve_port
from simulate import SCENARIOS, SimulatedRover


def create_app(
    mode: str,
    serial_port: Optional[str] = None,
    *,
    db_path: Optional[Path] = None,
) -> Tuple[Flask, Engine]:
    default_db = ROOT / ("mole-sim.db" if mode == "simulate" else "mole.db")
    db = Database(db_path or default_db)
    engine = Engine(mode, db)
    engine.serial_port = serial_port
    rover = SimulatedRover() if mode == "simulate" else RoverClient()
    app = Flask(__name__)
    stop_event = threading.Event()
    background_started = False
    last_rover_command = "stop"

    def rover_loop() -> None:
        while not stop_event.is_set():
            now = time.time()
            obj = rover.telemetry(now)
            with engine.lock:
                source = obj if obj is not None else rover.last
                data = dict(source) if isinstance(source, dict) else None
                if data is not None:
                    data["ir"] = explain_ir(
                        data.get("distance_cm"),
                        data.get("ir_obstacle"),
                        simulated=mode == "simulate",
                        driving=bool(data.get("driving")),
                    )
                if obj is None:
                    age = None if rover.last_ok is None else now - rover.last_ok
                    engine.rover = {
                        "ok": False,
                        "age_s": None if age is None else round(age, 2),
                        "data": data,
                        "error": rover.last_error or "not connected",
                    }
                else:
                    engine.rover = {"ok": True, "age_s": 0.0, "data": data, "error": None}
            stop_event.wait(0.5)

    def sim_loop() -> None:
        while not stop_event.is_set():
            for pkt in engine.sim.packets():
                engine.ingest_obj(pkt)
            stop_event.wait(1.0)

    def start_background() -> None:
        nonlocal background_started
        if background_started:
            return
        background_started = True
        threading.Thread(target=rover_loop, daemon=True).start()
        if mode == "simulate":
            engine.seed_simulated_history(40)
            threading.Thread(target=sim_loop, daemon=True).start()
            return
        if not serial_port:
            engine.serial_error = "Live mode needs --serial COMx"
            return
        reader = SerialReader(serial_port)

        def run() -> None:
            while not stop_event.is_set():
                try:
                    reader.open()
                    engine.serial_connected = True
                    engine.serial_error = None
                    while not stop_event.is_set():
                        obj = reader.read_obj()
                        if obj is not None:
                            engine.ingest_obj(obj)
                except Exception as exc:
                    engine.serial_connected = False
                    engine.serial_error = str(exc)
                    reader.close()
                    stop_event.wait(2.0)
            reader.close()

        threading.Thread(target=run, daemon=True).start()

    app.extensions["mole_start_background"] = start_background
    app.extensions["mole_stop_event"] = stop_event

    @app.get("/")
    def index():
        return send_from_directory(ROOT, "dashboard.html")

    @app.get("/monitoring")
    def monitoring():
        return send_from_directory(ROOT, "dashboard.html")

    @app.get("/rover")
    def rover_page():
        return send_from_directory(ROOT, "rover.html")

    @app.get("/assets/<path:filename>")
    def assets(filename: str):
        return send_from_directory(ROOT / "assets", filename)

    @app.get("/api/state")
    def state():
        return jsonify(engine.snapshot())

    @app.get("/api/export.csv")
    def export_csv():
        body = engine.db.export_csv()
        return Response(body, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=mole.csv"})

    @app.post("/api/baseline")
    def baseline():
        node_id = _node_id(request.get_json(silent=True))
        if node_id is None:
            return jsonify({"ok": False, "detail": "node_id must be 1 or 2"}), 400
        detail = engine.capture_baseline(node_id)
        return jsonify({"ok": not detail.startswith("No valid"), "detail": detail})

    @app.post("/api/ack")
    def ack():
        node_id = _node_id(request.get_json(silent=True))
        if node_id is None:
            return jsonify({"ok": False, "detail": "node_id must be 1 or 2"}), 400
        return jsonify({"ok": True, "detail": engine.ack(node_id)})

    @app.post("/api/clear")
    def clear():
        node_id = _node_id(request.get_json(silent=True))
        if node_id is None:
            return jsonify({"ok": False, "detail": "node_id must be 1 or 2"}), 400
        detail = engine.clear(node_id)
        ok = detail == "Latched alert cleared."
        return jsonify({"ok": ok, "detail": detail}), (200 if ok else 409)

    @app.post("/api/train")
    def train():
        node_id = _node_id(request.get_json(silent=True))
        if node_id is None:
            return jsonify({"ok": False, "detail": "node_id must be 1 or 2"}), 400
        ok, detail = engine.train(node_id)
        return jsonify({"ok": ok, "detail": detail}), (200 if ok else 400)

    @app.post("/api/calibration")
    def calibration():
        body = request.get_json(silent=True) or {}
        try:
            values = [float(body[key]) for key in ("adc0", "adc1", "mm0", "mm1")]
            engine.set_calibration(*values)
        except (KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "detail": str(exc)}), 400
        return jsonify({"ok": True, "detail": "Slider calibration saved. Node A AI baseline reset."})

    @app.post("/api/scenario")
    def scenario():
        if engine.mode != "simulate":
            return jsonify({"ok": False, "detail": "Scenarios are simulate-only."}), 400
        name = (request.get_json(silent=True) or {}).get("scenario")
        try:
            engine.sim.set_scenario(name)
        except ValueError:
            return jsonify({"ok": False, "detail": "Unknown scenario", "allowed": list(SCENARIOS)}), 400
        return jsonify({"ok": True, "scenario": name})

    @app.post("/api/rover/<cmd>")
    def rover_cmd(cmd: str):
        nonlocal last_rover_command
        result = rover.command(cmd)
        if result.get("ok") and cmd != last_rover_command:
            engine.db.log_event(
                time.time(),
                mode,
                None,
                "rover_command",
                f"Rover command: {cmd.upper()}.",
            )
            last_rover_command = cmd
        return jsonify(result), (200 if result.get("ok") else 503)

    @app.get("/api/rover/state")
    def rover_state():
        with engine.lock:
            return jsonify(
                {
                    "mode": mode,
                    "simulated": mode == "simulate",
                    "rover": engine.rover,
                    "last_command": last_rover_command,
                    "safety": "Hold-to-move. Release sends STOP. Firmware watchdog also stops after 400 ms.",
                }
            )

    return app, engine


def _node_id(body: object) -> Optional[int]:
    if not isinstance(body, dict):
        return None
    try:
        node_id = int(body.get("node_id"))
    except (TypeError, ValueError):
        return None
    return node_id if node_id in (1, 2) else None


def main() -> None:
    p = argparse.ArgumentParser(description="MOLE local monitoring website")
    p.add_argument("--mode", choices=("simulate", "live"), default="simulate")
    p.add_argument(
        "--serial",
        default=None,
        help="S3-Zero COM port (for example COM5), or 'auto'",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5000)
    args = p.parse_args()
    if args.mode == "live" and not args.serial:
        sys.exit("Live mode requires --serial COMx (S3-Zero USB). It will not fake data.")
    if args.mode == "live":
        try:
            args.serial = resolve_port(args.serial)
        except RuntimeError as exc:
            sys.exit(str(exc))
    app, _engine = create_app(args.mode, args.serial)
    app.extensions["mole_start_background"]()
    print(f"MOLE {args.mode} -> http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
