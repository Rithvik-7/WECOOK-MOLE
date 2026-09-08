from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Optional


FLAG_IMU = 1
FLAG_POT = 2
FLAG_VIB = 4
NODE_IDS = (1, 2)
SCHEMA = 1


@dataclass
class Telemetry:
    node_id: int
    seq: int
    uptime_ms: int
    valid: int
    roll_deg: Optional[float]
    pitch_deg: Optional[float]
    vibration_g: Optional[float]
    adc_raw: Optional[int]
    received_at: float
    gateway_ms: Optional[int] = None
    type: str = "telemetry"
    schema: int = SCHEMA

    @property
    def imu_ok(self) -> bool:
        return bool(self.valid & FLAG_IMU) and self.roll_deg is not None and self.pitch_deg is not None

    @property
    def vib_ok(self) -> bool:
        return bool(self.valid & FLAG_VIB) and self.vibration_g is not None

    @property
    def pot_ok(self) -> bool:
        return bool(self.valid & FLAG_POT) and self.adc_raw is not None


@dataclass
class RoverTelemetry:
    seq: int
    received_at: float
    distance_cm: Optional[float] = None
    ir_obstacle: bool = False
    mq7_raw: Optional[int] = None
    mq7_level: str = "UNKNOWN"
    roll_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    vibration_g: Optional[float] = None
    imu_valid: bool = False
    driving: bool = False
    device_id: str = "rover"


def _num(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        value = float(v)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def parse_telemetry(obj: dict[str, Any], received_at: float) -> Telemetry:
    if obj.get("type") != "telemetry":
        raise ValueError("not telemetry")
    if obj.get("schema") != SCHEMA:
        raise ValueError("bad schema")
    nid = int(obj["node_id"])
    if nid not in NODE_IDS:
        raise ValueError("bad node_id")
    valid = int(obj.get("valid") or 0)
    if valid < 0 or valid > 7:
        raise ValueError("bad valid mask")
    seq = int(obj["seq"])
    uptime_ms = int(obj.get("uptime_ms") or 0)
    if not 0 <= seq <= 0xFFFFFFFF or not 0 <= uptime_ms <= 0xFFFFFFFF:
        raise ValueError("bad counter")
    adc = obj.get("adc_raw")
    adc_i = None if adc is None else int(adc)
    if adc_i is not None and not 0 <= adc_i <= 4095:
        raise ValueError("bad adc")
    return Telemetry(
        node_id=nid,
        seq=seq,
        uptime_ms=uptime_ms,
        valid=valid,
        roll_deg=_num(obj.get("roll_deg")),
        pitch_deg=_num(obj.get("pitch_deg")),
        vibration_g=_num(obj.get("vibration_g")),
        adc_raw=adc_i,
        received_at=received_at,
        gateway_ms=None if obj.get("gateway_ms") is None else int(obj["gateway_ms"]),
    )
