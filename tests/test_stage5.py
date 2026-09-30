import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "firmware"))
import logic

from test_gateway import gateway


def sample(tilt, sequence, vibration=0.2, **extra):
    row = {"tilt_deg": tilt, "vibration": vibration, "valid": True, "sequence": sequence, "origin": "simulated", "sample_time": f"2026-09-27T10:0{sequence}:00+00:00"}
    row.update(extra)
    return row


def test_lcd_matches_rules_and_never_says_safe():
    steady = [sample(0.2, i) for i in range(6)]
    alarm = logic.local_alarm(steady)
    assert alarm["lcd"] == "NORMAL"
    assert alarm["buzzer"] is False
    assert "SAFE" not in alarm["lcd"]
    rising = [sample(0.2 + i * 0.8, i) for i in range(6)]
    movement = logic.local_alarm(rising)
    assert movement["condition"] == "movement"
    assert movement["lcd"] == "MOVEMENT"
    assert movement["buzzer"] is True
    shake = [sample(0.2, i, vibration=3) for i in range(6)]
    assert logic.local_alarm(shake)["condition"] == "watch"
    assert logic.local_alarm(shake)["buzzer"] is False


def test_gas_warmup_ir_and_fault_stay_honest():
    warmup = [sample(0.2, i, gas_raw=2000, gas_ready=False) for i in range(6)]
    assert logic.local_alarm(warmup)["condition"] == "normal"
    ready = [sample(0.2, i, gas_raw=2000, gas_ready=True) for i in range(6)]
    assert logic.local_alarm(ready)["condition"] == "gas"
    fault = [sample(0.2, i) for i in range(6)]
    fault[-1] = sample(0.2, 5, valid=False, fault=True, fault_reason="MPU missing")
    assert logic.local_alarm(fault)["condition"] == "sensor_fault"
    stale = [sample(0.2, i) for i in range(6)]
    stale[-1] = sample(0.2, 5, stale=True)
    assert logic.local_alarm(stale)["condition"] == "stale"
    packet = logic.build_packet("C", "boot-1", 0, {"tilt_deg": 0.2, "linear_raw": 40, "ir": 40, "temperature_ir": 30, "gas_raw": 10, "gas_ready": False})
    assert packet["linear_raw"] == 40
    assert "ir" not in packet
    assert "temperature_ir" not in packet
    assert packet["potentiometer_mm"] is None
    assert "not confirmed" in packet["linear_note"]


def test_receiver_is_a_star_and_drops_duplicates():
    receiver = logic.Receiver()
    packet = logic.build_packet("B", "boot-1", 1, {"tilt_deg": 1, "condition": "movement"})
    assert receiver.accept(packet, 0)["ok"] is True
    assert receiver.accept(packet, 1)["reason"] == "duplicate"
    relay = logic.build_packet("A", "boot-1", 1, {"tilt_deg": 0.2}, hops=2)
    assert receiver.accept(relay, 2)["reason"] == "not-a-star"
    old = logic.build_packet("B", "boot-1", 0, {"tilt_deg": 0.2})
    assert receiver.accept(old, 3)["reason"] == "stale-sequence"
    assert receiver.highest(0)["node_id"] == "B"
    assert receiver.highest(logic.FRESH_SECONDS + 1)["condition"] == "stale"
    assert logic.command_current(10, 11) is False
    assert logic.MAX_RETRIES == 3


def test_gateway_reports_overflow_without_dropping_stored_packets(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway, "QUEUE", tmp_path / "queue.db")
    monkeypatch.setattr(gateway, "MAX_PENDING", 1)
    gateway.enqueue({"sequence": 1})
    try:
        gateway.enqueue({"sequence": 2})
        raised = False
    except OverflowError:
        raised = True
    assert raised
    view = gateway.status()
    assert view["pending"] == 1
    assert view["overflows"] == 1
    assert view["last_success"] is None
    assert view["receiver_buffer"] is False
    assert view["rover_buffer"] is False
    header = (ROOT / "firmware" / "common" / "mole_logic.h").read_text(encoding="utf-8")
    assert "MOLE_HOP_LIMIT = 1" in header
    assert "MINE SAFE" not in header
