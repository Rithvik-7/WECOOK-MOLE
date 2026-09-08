from __future__ import annotations

import threading
from typing import Any, Optional

import requests

ROVER_BASE = "http://192.168.4.1"
COMMANDS = ("forward", "backward", "left", "right", "stop")


class RoverClient:
    def __init__(self, base: str = ROVER_BASE, timeout: float = 0.6):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.last_ok: Optional[float] = None
        self.last: Optional[dict[str, Any]] = None
        self.last_error: Optional[str] = None
        self._command_lock = threading.Lock()

    def command(self, name: str) -> dict[str, Any]:
        if name not in COMMANDS:
            return {"ok": False, "error": "unknown command"}
        with self._command_lock:
            try:
                r = requests.get(f"{self.base}/{name}", timeout=self.timeout)
                r.raise_for_status()
                return {"ok": True, "command": name}
            except Exception as exc:
                self.last_error = str(exc)
                return {"ok": False, "error": "rover unreachable"}

    def telemetry(self, now: float) -> Optional[dict[str, Any]]:
        try:
            r = requests.get(f"{self.base}/telemetry", timeout=self.timeout)
            r.raise_for_status()
            obj = r.json()
            if obj.get("device_id") == "rover" or obj.get("type") == "rover":
                self.last = obj
                self.last_ok = now
                self.last_error = None
                return obj
            self.last_error = "bad rover payload"
            return None
        except Exception as exc:
            self.last_error = str(exc)
            return None
