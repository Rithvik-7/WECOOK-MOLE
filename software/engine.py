from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from anomaly import JointAnomaly, NodeAnomaly
from calibration import relative_mm, tilt_change
from database import Database
from explain import compare_ab, compose
from features import feature_names, joint_vector, node_vector
from forecast import SeriesForecast
from models import Telemetry, parse_telemetry
from rules import (
    ALERT_MM,
    ALERT_TILT_DEG,
    CLEAR_NORMAL_SAMPLES,
    PERSIST_SAMPLES,
    STATUS_ALERT,
    STATUS_NORMAL,
    STATUS_UNKNOWN,
    STATUS_WATCH,
    WATCH_MM,
    WATCH_TILT_DEG,
    freshness,
    reason_text,
    sample_level,
)
from simulate import Simulator

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
HISTORY = 180


@dataclass
class NodeRuntime:
    node_id: int
    last: Optional[Telemetry] = None
    last_seq: Optional[int] = None
    last_uptime_ms: Optional[int] = None
    duplicates: int = 0
    out_of_order: int = 0
    packets_lost: int = 0
    roll0: Optional[float] = None
    pitch0: Optional[float] = None
    last_tilt: Optional[float] = None
    tilt: Optional[float] = None
    mm: Optional[float] = None
    persist: int = 0
    persist_level: str = STATUS_NORMAL
    status: str = STATUS_UNKNOWN
    latched_alert: bool = False
    acked: bool = False
    clear_normal: int = 0
    seen: bool = False
    reason: str = "No packets yet."
    history: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=HISTORY))
    forecast_tilt: SeriesForecast = field(
        default_factory=lambda: SeriesForecast(
            "tilt change", "deg", WATCH_TILT_DEG, ALERT_TILT_DEG
        )
    )
    forecast_vib: SeriesForecast = field(
        default_factory=lambda: SeriesForecast("vibration", "g")
    )
    forecast_gap: SeriesForecast = field(
        default_factory=lambda: SeriesForecast(
            "crack gap", "mm", WATCH_MM, ALERT_MM
        )
    )
    last_vec: Optional[list[float]] = None
    last_names: list[str] = field(default_factory=list)


class Engine:
    def __init__(self, mode: str, db: Database):
        if mode not in ("live", "simulate"):
            raise ValueError("mode must be live or simulate")
        self.mode = mode
        self.db = db
        self.lock = threading.RLock()
        self.nodes = {1: NodeRuntime(1), 2: NodeRuntime(2)}
        self.cal = {"adc0": None, "adc1": None, "mm0": None, "mm1": None}
        if mode == "simulate":
            # Demo millimetre scale only. Live mode requires a real two-point calibration.
            self.cal = {"adc0": 400.0, "adc1": 3600.0, "mm0": 0.0, "mm1": 20.0}
        self.sim = Simulator()
        self.anomaly = {
            1: NodeAnomaly(1, ARTIFACTS, load_existing=True),
            2: NodeAnomaly(2, ARTIFACTS, load_existing=True),
        }
        self.joint = JointAnomaly(ARTIFACTS)
        if mode == "live":
            stored_cal = self.db.get_setting("calibration", None)
            if isinstance(stored_cal, dict) and all(k in stored_cal for k in self.cal):
                self.cal = {key: stored_cal[key] for key in self.cal}
            for node_id, node in self.nodes.items():
                baseline = self.db.get_setting(f"baseline_{node_id}", None)
                if isinstance(baseline, dict):
                    node.roll0 = baseline.get("roll0")
                    node.pitch0 = baseline.get("pitch0")
        self.started = time.time()
        self.serial_error: Optional[str] = None
        self.serial_connected = False
        self.serial_port: Optional[str] = None
        self.rover: dict[str, Any] = {"ok": False, "age_s": None, "data": None, "error": None}
        self.dropped = 0

    def crack_calibrated(self) -> bool:
        return None not in self.cal.values()

    def set_calibration(self, adc0: float, adc1: float, mm0: float, mm1: float) -> None:
        if abs(float(adc1) - float(adc0)) < 1.0:
            raise ValueError("adc0 and adc1 must be different points")
        with self.lock:
            self.cal = {"adc0": float(adc0), "adc1": float(adc1), "mm0": float(mm0), "mm1": float(mm1)}
            if self.mode == "live":
                self.db.set_setting("calibration", self.cal)
            n = self.nodes[1]
            if n.last is not None and n.last.adc_raw is not None:
                n.mm = relative_mm(n.last.adc_raw, self.cal["adc0"], self.cal["adc1"], self.cal["mm0"], self.cal["mm1"])
            self.anomaly[1].reset()
            self.joint.reset()
            self.db.log_event(time.time(), self.mode, 1, "calibration", "Slider millimetre scale set; AI reset.")

    def capture_baseline(self, node_id: int) -> str:
        with self.lock:
            n = self.nodes[node_id]
            if n.last is None or not n.last.imu_ok:
                return "No valid IMU sample to capture."
            n.roll0 = n.last.roll_deg
            n.pitch0 = n.last.pitch_deg
            n.last_tilt = 0.0
            if self.mode == "live":
                self.db.set_setting(
                    f"baseline_{node_id}",
                    {"roll0": n.roll0, "pitch0": n.pitch0},
                )
            self.anomaly[node_id].reset()
            self.joint.reset()
            self.db.log_event(time.time(), self.mode, node_id, "baseline", "Orientation baseline captured; AI reset.")
            return f"Baseline captured for node {node_id}."

    def ack(self, node_id: int) -> str:
        with self.lock:
            n = self.nodes[node_id]
            n.acked = True
            self.db.log_event(time.time(), self.mode, node_id, "ack", "Operator acknowledged. Event kept.")
            return "Acknowledged. The event stays in history."

    def clear(self, node_id: int) -> str:
        with self.lock:
            n = self.nodes[node_id]
            if n.status != STATUS_NORMAL or n.clear_normal < CLEAR_NORMAL_SAMPLES:
                return "Clear needs three fresh NORMAL samples after recovery."
            n.latched_alert = False
            n.acked = False
            n.clear_normal = 0
            self.db.log_event(time.time(), self.mode, node_id, "clear", "Latched alert cleared after recovery.")
            return "Latched alert cleared."

    def inspection_done(self) -> tuple[bool, str]:
        """Operator finished rover inspection. Closes recovered ALERT latches on A and B.

        Live ALERT stays ALERT. History is kept. ML cannot call this.
        """
        with self.lock:
            letters = {1: "A", 2: "B"}
            cleared: list[str] = []
            still_alert: list[str] = []
            any_latch = False
            for nid, n in self.nodes.items():
                if not n.latched_alert:
                    continue
                any_latch = True
                n.acked = True
                if n.status == STATUS_ALERT:
                    still_alert.append(letters[nid])
                    continue
                n.latched_alert = False
                n.acked = False
                n.clear_normal = 0
                cleared.append(letters[nid])
            if still_alert:
                names = " and ".join(f"Node {name}" for name in still_alert)
                verb = "are" if len(still_alert) > 1 else "is"
                detail = (
                    f"Inspection recorded. History kept. {names} {verb} still over the "
                    "tabletop ALERT threshold — recover the mount, then click Inspection done again."
                )
            elif cleared:
                names = " and ".join(f"Node {name}" for name in cleared)
                detail = (
                    f"Inspection done. Latched alert closed on {names}. "
                    "The event stays in history. This is not a mine-safety certification."
                )
            elif not any_latch:
                detail = "Inspection recorded. No latched alert to close."
            else:
                detail = "Inspection recorded. History kept."
            self.db.log_event(
                time.time(),
                self.mode,
                None,
                "inspection_done",
                detail,
            )
            return (not still_alert), detail

    def train(self, node_id: int) -> tuple[bool, str]:
        with self.lock:
            n = self.nodes[node_id]
            blocked = n.latched_alert or n.status in (STATUS_WATCH, STATUS_ALERT, STATUS_UNKNOWN)
            ok, msg = self.anomaly[node_id].can_train(live=(self.mode == "live"), latched_or_watch=blocked)
            if not ok:
                return False, msg
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            text = self.anomaly[node_id].train(stamp)
            self.db.log_event(time.time(), self.mode, node_id, "train", text)
            return True, text

    def ingest_obj(self, obj: dict[str, Any], received_at: Optional[float] = None) -> None:
        now = time.time() if received_at is None else received_at
        if obj.get("type") == "status":
            return
        try:
            pkt = parse_telemetry(obj, now)
        except (KeyError, TypeError, ValueError):
            self.dropped += 1
            return
        with self.lock:
            self._ingest_locked(pkt, obj)

    def _ingest_locked(self, pkt: Telemetry, obj: dict[str, Any]) -> None:
        n = self.nodes[pkt.node_id]
        if n.last_seq is not None and pkt.seq == n.last_seq:
            n.duplicates += 1
            return
        if (
            n.last_seq is not None
            and pkt.seq < n.last_seq
            and n.last_uptime_ms is not None
            and pkt.uptime_ms >= n.last_uptime_ms
        ):
            n.out_of_order += 1
            self.dropped += 1
            return
        rebooted = (
            n.last_uptime_ms is not None
            and pkt.uptime_ms < n.last_uptime_ms
        )
        if rebooted:
            self.db.log_event(
                pkt.received_at,
                self.mode,
                pkt.node_id,
                "reboot",
                "Node uptime restarted; sequence tracking reset.",
            )
        elif n.last_seq is not None and pkt.seq > n.last_seq + 1:
            n.packets_lost += pkt.seq - n.last_seq - 1
        n.last_seq = pkt.seq
        n.last_uptime_ms = pkt.uptime_ms
        n.last = pkt
        n.seen = True
        self.db.log_packet(pkt.received_at, self.mode, pkt.node_id, pkt.seq, obj)

        tchg = tilt_change(pkt.roll_deg, pkt.pitch_deg, n.roll0, n.pitch0)
        if tchg is None and pkt.imu_ok and self.mode == "simulate":
            tchg = tilt_change(pkt.roll_deg, pkt.pitch_deg, 0.0, 0.0)
        n.tilt = tchg
        mm = None
        if pkt.node_id == 1 and pkt.adc_raw is not None:
            mm = relative_mm(pkt.adc_raw, self.cal["adc0"], self.cal["adc1"], self.cal["mm0"], self.cal["mm1"])
        n.mm = mm
        d_tilt = None if tchg is None or n.last_tilt is None else tchg - n.last_tilt
        if tchg is not None:
            n.last_tilt = tchg

        stale = False
        level = sample_level(
            tchg,
            mm,
            node_id=pkt.node_id,
            crack_calibrated=self.crack_calibrated() if pkt.node_id == 1 else True,
            imu_ok=pkt.imu_ok,
        )
        if n.persist_level == level:
            n.persist += 1
        else:
            n.persist_level = level
            n.persist = 1

        previous_status = n.status
        if level == STATUS_UNKNOWN:
            n.status = STATUS_UNKNOWN
        elif n.persist >= PERSIST_SAMPLES:
            n.status = level
        # else keep previous status until persistence, but never stay NORMAL on first UNKNOWN
        if level == STATUS_ALERT and n.persist >= PERSIST_SAMPLES:
            if not n.latched_alert:
                self.db.log_event(pkt.received_at, self.mode, pkt.node_id, "alert", "ALERT latched.")
            n.latched_alert = True
        if level == STATUS_NORMAL:
            n.clear_normal += 1
        else:
            n.clear_normal = 0
        if n.status != previous_status:
            if n.status == STATUS_WATCH:
                self.db.log_event(
                    pkt.received_at, self.mode, pkt.node_id, "watch", "Status changed to WATCH."
                )
            elif n.status == STATUS_NORMAL and previous_status not in (STATUS_UNKNOWN,):
                self.db.log_event(
                    pkt.received_at, self.mode, pkt.node_id, "recovered", "Status returned to NORMAL."
                )

        n.reason = reason_text(
            node_id=pkt.node_id,
            status=n.status,
            tilt=tchg,
            mm=mm,
            stale=stale,
            imu_ok=pkt.imu_ok,
            crack_calibrated=self.crack_calibrated() if pkt.node_id == 1 else True,
            persist=n.persist,
        )

        n.forecast_tilt.push(tchg, pkt.received_at)
        n.forecast_vib.push(
            pkt.vibration_g if pkt.vib_ok else None, pkt.received_at
        )
        if pkt.node_id == 1:
            n.forecast_gap.push(mm, pkt.received_at)
        n.history.append(
            {
                "t": pkt.received_at,
                "tilt": tchg,
                "vib": pkt.vibration_g,
                "mm": mm,
                "roll": pkt.roll_deg,
                "pitch": pkt.pitch_deg,
            }
        )

        include_mm = pkt.node_id == 1 and self.crack_calibrated()
        vec = node_vector(
            tchg,
            pkt.vibration_g if pkt.vib_ok else None,
            0.0 if d_tilt is None else d_tilt,
            mm,
            node_id=pkt.node_id,
            include_mm=include_mm,
        )
        names = feature_names(pkt.node_id, include_mm)
        if vec is not None and n.status == STATUS_NORMAL and not n.latched_alert:
            self.anomaly[pkt.node_id].note_healthy(vec, names)
            if self.mode == "simulate":
                fitted = self.anomaly[pkt.node_id].maybe_fit_simulation()
                if fitted:
                    self.db.log_event(pkt.received_at, self.mode, pkt.node_id, "train", fitted)
        n.last_vec = vec
        n.last_names = names
        self._update_joint_locked()

    def _update_joint_locked(self) -> None:
        a = self.nodes[1]
        b = self.nodes[2]
        row = joint_vector(
            a.tilt,
            b.tilt,
            None if a.last is None else a.last.vibration_g,
            None if b.last is None else b.last.vibration_g,
        )
        if (
            row is not None
            and a.status == STATUS_NORMAL
            and b.status == STATUS_NORMAL
            and not a.latched_alert
            and not b.latched_alert
        ):
            self.joint.note_healthy(row)
            self.joint.maybe_fit(simulated=self.mode == "simulate")

    def tick_stale(self, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self.lock:
            for n in self.nodes.values():
                if n.last is None:
                    n.status = STATUS_UNKNOWN
                    n.reason = reason_text(
                        node_id=n.node_id, status=STATUS_UNKNOWN, tilt=None, mm=None,
                        stale=True, imu_ok=False,
                        crack_calibrated=self.crack_calibrated() if n.node_id == 1 else True,
                        persist=0,
                    )
                    continue
                if freshness(now, n.last.received_at) == STATUS_UNKNOWN:
                    n.status = STATUS_UNKNOWN
                    n.reason = reason_text(
                        node_id=n.node_id, status=STATUS_UNKNOWN, tilt=n.tilt, mm=n.mm,
                        stale=True, imu_ok=True,
                        crack_calibrated=self.crack_calibrated() if n.node_id == 1 else True,
                        persist=n.persist,
                    )

    def seed_simulated_history(self, seconds: int = 40) -> None:
        """Pre-fill simulate mode so charts and Ridge forecasts are ready immediately."""
        if self.mode != "simulate":
            return
        now = time.time()
        for i in range(max(0, int(seconds))):
            received_at = now - (seconds - i)
            for pkt in self.sim.packets():
                self.ingest_obj(pkt, received_at=received_at)

    def snapshot(self, now: Optional[float] = None) -> dict[str, Any]:
        self.tick_stale(now)
        now = time.time() if now is None else now
        with self.lock:
            cards = {}
            ai = {}
            forecasts = {}
            for nid, n in self.nodes.items():
                age = None if n.last is None else now - n.last.received_at
                include_mm = nid == 1 and self.crack_calibrated()
                names = n.last_names or feature_names(nid, include_mm)
                vec = n.last_vec
                ar = self.anomaly[nid].score_row(vec, names)
                # Display status: latched ALERT stays visible as ALERT even if recovered to NORMAL until clear
                shown = n.status
                if n.latched_alert and n.status == STATUS_NORMAL:
                    shown = STATUS_NORMAL
                cards[str(nid)] = {
                    "node_id": nid,
                    "seen": n.seen,
                    "status": shown if n.seen else STATUS_UNKNOWN,
                    "latched_alert": n.latched_alert,
                    "acked": n.acked,
                    "age_s": None if age is None else round(age, 2),
                    "seq": None if n.last is None else n.last.seq,
                    "packets_lost": n.packets_lost,
                    "duplicates": n.duplicates,
                    "out_of_order": n.out_of_order,
                    "roll_deg": None if n.last is None else n.last.roll_deg,
                    "pitch_deg": None if n.last is None else n.last.pitch_deg,
                    "vibration_g": None if n.last is None else n.last.vibration_g,
                    "adc_raw": None if n.last is None else n.last.adc_raw,
                    "tilt_change_deg": None if n.tilt is None else round(n.tilt, 3),
                    "relative_mm": None if n.mm is None else round(n.mm, 3),
                    "baseline": n.roll0 is not None,
                    "imu_ok": None if n.last is None else n.last.imu_ok,
                    "pot_ok": None if n.last is None else n.last.pot_ok,
                    "reason": n.reason,
                    "history": list(n.history)[-90:],
                    "valid": None if n.last is None else n.last.valid,
                }
                ai[str(nid)] = {
                    "state": ar.state,
                    "score": None if ar.score is None else round(ar.score, 4),
                    "top_feature": ar.top_feature,
                    "n_train": ar.n_train,
                    "min_train": ar.min_train,
                    "trained_at": ar.trained_at,
                    "feature_names": ar.feature_names,
                    "reason": ar.reason,
                    "model": "sklearn IsolationForest + LocalOutlierFactor",
                    "isolation_state": ar.isolation_state,
                    "lof_state": ar.lof_state,
                    "votes": ar.votes,
                    "simulated": ar.simulated,
                    "prior": ar.prior,
                    "models": ar.models,
                    "contamination": 0.05,
                    "can_train": self.mode == "live",
                }
                ft = n.forecast_tilt.predict()
                fv = n.forecast_vib.predict()
                fg = n.forecast_gap.predict() if nid == 1 else None
                forecasts[str(nid)] = {
                    "tilt": ft,
                    "vibration": fv,
                    "gap": fg,
                    "label": ft["label"],
                }
            a_tilt = self.nodes[1].tilt
            b_tilt = self.nodes[2].tilt
            a_vib = None if self.nodes[1].last is None else self.nodes[1].last.vibration_g
            b_vib = None if self.nodes[2].last is None else self.nodes[2].last.vibration_g
            ab = compare_ab(a_tilt, b_tilt)
            joint = self.joint.score(joint_vector(a_tilt, b_tilt, a_vib, b_vib), a_tilt, b_tilt)
            explanation = compose(
                rule_a=cards["1"]["reason"],
                rule_b=cards["2"]["reason"],
                ai_a=ai["1"]["reason"],
                ai_b=ai["2"]["reason"],
                ab=ab,
                forecast_note=forecasts["1"]["tilt"].get("reason") or "",
            )
            statuses = [node.status for node in self.nodes.values()]
            latched = [n for n in self.nodes.values() if n.latched_alert]
            if STATUS_ALERT in statuses or latched:
                system_status = STATUS_ALERT
                recovered_latch = latched and all(n.status != STATUS_ALERT for n in latched)
                if recovered_latch:
                    next_action = "Rover inspection can finish the loop. Click Inspection done to close the latched alert. History stays."
                else:
                    next_action = "Review evidence, inspect with the rover, then click Inspection done."
            elif STATUS_UNKNOWN in statuses:
                system_status = STATUS_UNKNOWN
                a_stale = freshness(now, self.nodes[1].last.received_at if self.nodes[1].last else None) == STATUS_UNKNOWN
                b_stale = freshness(now, self.nodes[2].last.received_at if self.nodes[2].last else None) == STATUS_UNKNOWN
                if a_stale or b_stale:
                    next_action = "Restore fresh, valid node data before interpreting conditions. Close Serial Monitor; keep the S3 receiver on USB."
                elif self.nodes[1].roll0 is None or self.nodes[2].roll0 is None:
                    next_action = "Nodes are live. Keep mounts still, then click Baseline A and Baseline B."
                elif not self.crack_calibrated():
                    next_action = "Baseline is set. Open Slider two-point calibration and save two ADC/mm points."
                else:
                    next_action = "Restore fresh, valid node data before interpreting conditions."
            elif STATUS_WATCH in statuses:
                system_status = STATUS_WATCH
                next_action = "Watch the trend. Prepare rover inspection if the change persists."
            else:
                system_status = STATUS_NORMAL
                next_action = "Continue monitoring. NORMAL is not a mine-safety certification."
            # Node B must never cancel Node A latch — already separate objects.
            return {
                "mode": self.mode,
                "simulated": self.mode == "simulate",
                "scenario": self.sim.scenario if self.mode == "simulate" else None,
                "now": now,
                "serial_error": self.serial_error,
                "serial_connected": self.serial_connected,
                "serial_port": self.serial_port,
                "dropped": self.dropped,
                "calibration": {
                    "slider_ready": self.crack_calibrated(),
                    **{k: self.cal[k] for k in self.cal},
                },
                "nodes": cards,
                "ai": ai,
                "joint": joint,
                "forecast": forecasts,
                "compare": ab,
                "explanation": explanation,
                "ml_stack": {
                    "detectors": [
                        "IsolationForest (per node)",
                        "LocalOutlierFactor novelty (per node)",
                        "IsolationForest on A–B residual",
                    ],
                    "forecasters": ["Ridge", "HuberRegressor", "LinearRegression", "persistence baseline"],
                    "selection": "lowest holdout MAE",
                    "label": "sklearn only. No LLM. No collapse probability. ML cannot clear a rule latch.",
                },
                "system_status": system_status,
                "next_action": next_action,
                "rover": self.rover,
                "events": self.db.recent_events(),
                "database": self.db.counts(),
                "honesty": "Green is healthy data, not a certified-safe mine. Forecast is 30 s of signals, not collapse probability.",
            }
