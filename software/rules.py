from __future__ import annotations

from typing import Optional

WATCH_TILT_DEG = 3.0
ALERT_TILT_DEG = 6.0
WATCH_MM = 2.0
ALERT_MM = 4.0
PERSIST_SAMPLES = 3
STALE_SECONDS = 5.0
CLEAR_NORMAL_SAMPLES = 3

STATUS_NORMAL = "NORMAL"
STATUS_WATCH = "WATCH"
STATUS_ALERT = "ALERT"
STATUS_UNKNOWN = "UNKNOWN"


def freshness(now: float, last_received: Optional[float]) -> str:
    if last_received is None:
        return STATUS_UNKNOWN
    if (now - last_received) > STALE_SECONDS:
        return STATUS_UNKNOWN
    return "FRESH"


def sample_level(tilt: Optional[float], mm: Optional[float], *, node_id: int,
                 crack_calibrated: bool, imu_ok: bool) -> str:
    if not imu_ok:
        return STATUS_UNKNOWN
    if tilt is None:
        return STATUS_UNKNOWN
    if node_id == 1 and not crack_calibrated:
        return STATUS_UNKNOWN
    t = tilt if tilt is not None else 0.0
    m = 0.0 if mm is None else mm
    if node_id != 1:
        m = 0.0
    if t >= ALERT_TILT_DEG or m >= ALERT_MM:
        return STATUS_ALERT
    if t >= WATCH_TILT_DEG or m >= WATCH_MM:
        return STATUS_WATCH
    return STATUS_NORMAL


def reason_text(*, node_id: int, status: str, tilt: Optional[float], mm: Optional[float],
                stale: bool, imu_ok: bool, crack_calibrated: bool, persist: int) -> str:
    if stale:
        return f"Node {node_id}: no fresh packet in {STALE_SECONDS:.0f} s → UNKNOWN."
    if not imu_ok:
        return f"Node {node_id}: IMU not valid. Not a healthy reading."
    if tilt is None:
        return f"Node {node_id}: capture an orientation baseline before NORMAL."
    if node_id == 1 and not crack_calibrated:
        return "Node A slider is not millimetre-calibrated. Cannot show NORMAL."
    t = 0.0 if tilt is None else tilt
    m = 0.0 if mm is None else mm
    if status == STATUS_ALERT:
        bits = []
        if t >= ALERT_TILT_DEG:
            bits.append(f"tilt change {t:.2f}° (≥ {ALERT_TILT_DEG:.0f}°)")
        if node_id == 1 and m >= ALERT_MM:
            bits.append(f"gap {m:.2f} mm (≥ {ALERT_MM:.0f} mm)")
        extra = ", ".join(bits) if bits else f"tilt {t:.2f}°"
        return f"Node {node_id} ALERT after {persist} consecutive samples: {extra}."
    if status == STATUS_WATCH:
        bits = []
        if t >= WATCH_TILT_DEG:
            bits.append(f"tilt change {t:.2f}° (≥ {WATCH_TILT_DEG:.0f}°)")
        if node_id == 1 and m >= WATCH_MM:
            bits.append(f"gap {m:.2f} mm (≥ {WATCH_MM:.0f} mm)")
        extra = ", ".join(bits) if bits else f"tilt {t:.2f}°"
        return f"Node {node_id} WATCH after {persist} consecutive samples: {extra}."
    return f"Node {node_id} NORMAL. Tilt change {t:.2f}°" + (f", gap {m:.2f} mm." if node_id == 1 else ".")
