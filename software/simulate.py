from __future__ import annotations

import math
import threading
from typing import Any, Optional


SCENARIOS = ("normal", "rising", "watch", "alert", "offline", "sensor_fault")


class Simulator:
    def __init__(self) -> None:
        self.scenario = "normal"
        self.seq = {1: 0, 2: 0}
        self.uptime = {1: 0, 2: 0}
        self.tick = 0

    def set_scenario(self, name: str) -> None:
        if name not in SCENARIOS:
            raise ValueError("unknown scenario")
        self.scenario = name
        self.tick = 0

    def _base(self, node_id: int, roll, pitch, vib, adc, valid: int) -> dict[str, Any]:
        self.seq[node_id] += 1
        self.uptime[node_id] += 1000
        return {
            "type": "telemetry",
            "schema": 1,
            "node_id": node_id,
            "seq": self.seq[node_id],
            "uptime_ms": self.uptime[node_id],
            "gateway_ms": self.uptime[node_id] + 80,
            "valid": valid,
            "roll_deg": roll,
            "pitch_deg": pitch,
            "vibration_g": vib,
            "adc_raw": adc,
        }

    def packets(self) -> list[dict[str, Any]]:
        self.tick += 1
        s = self.scenario
        if s == "offline":
            return []
        if s == "sensor_fault":
            return [
                self._base(1, None, None, None, None, 0),
                self._base(2, 0.05, 0.04, 0.004, None, 5),
            ]
        wave = math.sin(self.tick / 4.0)
        if s == "rising":
            roll = min(7.2, 0.2 + self.tick * 0.18)
            adc = min(1500, 400 + self.tick * 22)
            return [
                self._base(1, roll, 0.12, 0.006 + abs(wave) * 0.004, adc, 7),
                self._base(2, 0.10 + wave * 0.02, 0.06, 0.003, None, 5),
            ]
        if s == "watch":
            return [
                self._base(1, 3.4 + wave * 0.08, 0.4, 0.02, 400, 7),
                self._base(2, 0.12 + wave * 0.02, 0.08, 0.006, None, 5),
            ]
        if s == "alert":
            return [
                self._base(1, 6.8, 1.1, 0.05, 400, 7),
                self._base(2, 0.18, 0.10, 0.008, None, 5),
            ]
        return [
            self._base(1, 0.15 + wave * 0.025, -0.08, 0.004 + abs(wave) * 0.001, 400, 7),
            self._base(2, 0.10 + wave * 0.02, 0.06, 0.003 + abs(wave) * 0.0007, None, 5),
        ]


class SimulatedRover:
    """Safe rover stand-in used only when the whole app is in simulate mode."""

    def __init__(self) -> None:
        self.command_name = "stop"
        self.seq = 0
        self.last_ok: Optional[float] = None
        self.last: Optional[dict[str, Any]] = None
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()
        self._approach: Optional[float] = None

    def command(self, name: str) -> dict[str, Any]:
        if name not in ("forward", "backward", "left", "right", "stop"):
            return {"ok": False, "error": "unknown command"}
        with self._lock:
            self.command_name = name
            if name == "stop":
                self._approach = None
            else:
                if self._approach is None:
                    self._approach = 48.0
                self._approach = max(6.0, self._approach - 1.15)
        return {"ok": True, "simulated": True, "command": name}

    def telemetry(self, now: float) -> dict[str, Any]:
        self.seq += 1
        with self._lock:
            command_name = self.command_name
            if command_name != "stop" and self._approach is not None:
                distance = self._approach
            elif command_name != "stop":
                self._approach = 48.0
                distance = self._approach
            else:
                self._approach = None
                distance = 42.0 + 3.0 * math.sin(self.seq / 9.0)
            obstacle = distance < 12.0
            payload = {
                "type": "rover",
                "device_id": "rover",
                "seq": self.seq,
                "uptime_ms": self.seq * 500,
                "distance_cm": round(distance, 1),
                "ir_obstacle": obstacle,
                "mq7_raw": 1260 + int(25 * math.sin(self.seq / 5.0)),
                "mq7_level": "NORMAL",
                "roll_deg": round(1.2 * math.sin(self.seq / 8.0), 2),
                "pitch_deg": round(0.8 * math.cos(self.seq / 7.0), 2),
                "vibration_g": 0.018 if command_name != "stop" else 0.003,
                "imu_valid": True,
                "driving": command_name != "stop",
                "command": command_name,
            }
        self.last = payload
        self.last_ok = now
        return payload
