"""Host-side node and receiver behaviour.

The same thresholds are used by the API rules. Pins are not read here.
IR values stay raw. Potentiometer millimetres are never produced.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from analysis import classify_window

VERSION = 1
HOP_LIMIT = 1
MAX_RETRIES = 3
FRESH_SECONDS = 120
RANK = {"normal": 0, "unavailable": 1, "watch": 2, "stale": 3, "sensor_fault": 4, "gas": 5, "movement": 5}

LCD = {
    "normal": "NORMAL",
    "watch": "WATCH",
    "movement": "MOVEMENT",
    "gas": "GAS",
    "sensor_fault": "SENSOR FAULT",
    "stale": "STALE",
    "unavailable": "UNAVAILABLE",
}


def lcd_label(condition: str) -> str:
    text = LCD[condition]
    if "SAFE" in text:
        raise RuntimeError("LCD text must not claim the mine is safe")
    return text


def buzzer_on(condition: str) -> bool:
    return condition in {"movement", "gas", "sensor_fault", "stale"}


def local_alarm(samples: list[dict]) -> dict:
    result = classify_window(samples, [])
    condition = result["condition"]
    return {"condition": condition, "lcd": lcd_label(condition), "buzzer": buzzer_on(condition), "summary": result["summary"]}


def build_packet(node_id: str, session_id: str, sequence: int, readings: dict, hops: int = 1) -> dict:
    packet = {
        "version": VERSION,
        "node_id": node_id,
        "session_id": session_id,
        "sequence": sequence,
        "origin": "physical",
        "hops": hops,
        "valid": readings.get("valid", True),
        "potentiometer_mm": None,
    }
    packet.update(readings)
    packet.pop("temperature_ir", None)
    packet.pop("ir", None)
    if node_id not in {"A", "C"}:
        packet.pop("potentiometer_raw", None)
        packet.pop("slider_raw", None)
    else:
        packet["potentiometer_mm"] = None
        packet["slider_note"] = "Slider counts are not millimetres until the slider is fixed and calibrated."
    if node_id != "B":
        packet.pop("temperature_signal_raw", None)
    else:
        packet["temperature_note"] = "DS18B20 air temperature in degrees Celsius. Not soil moisture or groundwater."
    if node_id != "C":
        packet.pop("gas_raw", None)
        packet.pop("gas_ready", None)
        packet.pop("linear_raw", None)
    else:
        packet["linear_note"] = "Linear sensor model is not confirmed. Counts are not millimetres."
    if node_id != "D":
        packet.pop("humidity_pct", None)
        packet.pop("pressure_hpa", None)
    if node_id not in {"B", "D"}:
        packet.pop("temperature_c", None)
    return packet


def command_current(expires_at: float, now: float) -> bool:
    return now < expires_at


class Receiver:
    """Star collector. It keeps the latest packet per node for the LCD only."""

    def __init__(self) -> None:
        self.seen: set[tuple] = set()
        self.last_sequence: dict[tuple, int] = {}
        self.latest: dict[str, dict] = {}
        self.boot_id = "receiver-boot"

    def accept(self, packet: dict, now_s: float) -> dict:
        if packet.get("version") != VERSION:
            return {"ok": False, "reason": "version"}
        if int(packet.get("hops", 1)) > HOP_LIMIT:
            return {"ok": False, "reason": "not-a-star"}
        if packet.get("node_id") not in {"A", "B", "C", "D"}:
            return {"ok": False, "reason": "node"}
        key = (packet["node_id"], packet["session_id"], packet["sequence"])
        if key in self.seen:
            return {"ok": False, "reason": "duplicate"}
        previous = self.last_sequence.get((packet["node_id"], packet["session_id"]))
        if previous is not None and packet["sequence"] < previous:
            return {"ok": False, "reason": "stale-sequence"}
        self.seen.add(key)
        self.last_sequence[(packet["node_id"], packet["session_id"])] = packet["sequence"]
        self.latest[packet["node_id"]] = {"packet": packet, "at": now_s}
        return {"ok": True, "forward": {k: v for k, v in packet.items() if k not in {"version", "hops"}}}

    def highest(self, now_s: float) -> dict:
        best = {"node_id": None, "condition": "unavailable", "lcd": "UNAVAILABLE"}
        for node_id, item in self.latest.items():
            condition = "stale" if now_s - item["at"] > FRESH_SECONDS else item["packet"].get("condition", "unavailable")
            if RANK[condition] >= RANK[best["condition"]]:
                best = {"node_id": node_id, "condition": condition, "lcd": lcd_label(condition)}
        return best
