from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from database import Database
from engine import Engine
from models import parse_telemetry
from rules import STATUS_ALERT, STATUS_NORMAL, STATUS_UNKNOWN, STATUS_WATCH
from app import create_app


def engine_sim(tmp_path: Path) -> Engine:
    return Engine("simulate", Database(tmp_path / "t.db"))


def engine_live(tmp_path: Path) -> Engine:
    return Engine("live", Database(tmp_path / "t.db"))


def pkt(node_id, seq, roll=0.1, pitch=0.0, vib=0.004, adc=400, valid=None, **kw):
    if valid is None:
        valid = 7 if node_id == 1 else 5
    if node_id == 2:
        adc = None
        valid = 5 if valid == 7 else valid
    d = {
        "type": "telemetry",
        "schema": 1,
        "node_id": node_id,
        "seq": seq,
        "uptime_ms": seq * 1000,
        "valid": valid,
        "roll_deg": roll,
        "pitch_deg": pitch,
        "vibration_g": vib,
        "adc_raw": adc,
    }
    d.update(kw)
    return d


def pump(eng: Engine, node_id, n, seq0=1, **kw):
    t0 = 1_000_000.0
    for i in range(n):
        eng.ingest_obj(pkt(node_id, seq0 + i, **kw), received_at=t0 + i)


def test_unseen_never_green(tmp_path):
    snap = engine_sim(tmp_path).snapshot(now=1_000_000.0)
    assert snap["nodes"]["1"]["status"] == STATUS_UNKNOWN
    assert snap["nodes"]["2"]["status"] == STATUS_UNKNOWN
    assert snap["nodes"]["1"]["seen"] is False


def test_simulate_cannot_train(tmp_path):
    eng = engine_sim(tmp_path)
    pump(eng, 1, 5, roll=0.1)
    pump(eng, 2, 5, roll=0.1)
    ok, msg = eng.train(1)
    assert ok is False
    assert "simulated" in msg.lower()


def test_missing_crack_scale_blocks_normal(tmp_path):
    eng = engine_live(tmp_path)
    t0 = 2_000_000.0
    for i in range(4):
        eng.ingest_obj(pkt(1, i + 1, roll=0.2), received_at=t0 + i)
    eng.capture_baseline(1)
    for i in range(4, 8):
        eng.ingest_obj(pkt(1, i + 1, roll=0.2), received_at=t0 + i)
    snap = eng.snapshot(now=t0 + 8)
    assert snap["nodes"]["1"]["status"] == STATUS_UNKNOWN
    assert "calibrat" in snap["nodes"]["1"]["reason"].lower()


def test_watch_and_alert_latch_ack_clear(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 3_000_000.0
    for i in range(4):
        eng.ingest_obj(pkt(1, i + 1, roll=6.8, pitch=0.2), received_at=t0 + i)
    n = eng.nodes[1]
    assert n.status == STATUS_ALERT
    assert n.latched_alert is True
    eng.ack(1)
    assert n.acked is True
    assert n.latched_alert is True
    for i in range(4, 10):
        eng.ingest_obj(pkt(1, i + 1, roll=0.1, pitch=0.0), received_at=t0 + i)
    assert n.status == STATUS_NORMAL
    assert n.latched_alert is True
    msg = eng.clear(1)
    assert "cleared" in msg.lower()
    assert n.latched_alert is False


def test_node_a_adc_without_pot_flag_still_scales(tmp_path):
    eng = engine_live(tmp_path)
    eng.set_calibration(100, 2100, 0, 10)
    t0 = 6_000_000.0
    eng.ingest_obj(pkt(1, 1, roll=0.2, adc=1100, valid=5), received_at=t0)
    snap = eng.snapshot(now=t0 + 0.2)
    assert snap["nodes"]["1"]["adc_raw"] == 1100
    assert snap["nodes"]["1"]["relative_mm"] == 5.0


def test_set_calibration_updates_last_gap(tmp_path):
    eng = engine_live(tmp_path)
    t0 = 6_100_000.0
    eng.ingest_obj(pkt(1, 1, roll=0.2, adc=3376, valid=7), received_at=t0)
    eng.set_calibration(3376, 2759, 0, 10)
    snap = eng.snapshot(now=t0 + 0.2)
    assert snap["calibration"]["slider_ready"] is True
    assert snap["nodes"]["1"]["relative_mm"] == 0.0


def test_next_action_asks_for_baseline_when_fresh(tmp_path):
    eng = engine_live(tmp_path)
    t0 = 5_500_000.0
    eng.ingest_obj(pkt(1, 1, roll=0.2), received_at=t0)
    eng.ingest_obj(pkt(2, 1, roll=0.1), received_at=t0)
    snap = eng.snapshot(now=t0 + 0.4)
    assert snap["system_status"] == STATUS_UNKNOWN
    assert "Baseline" in snap["next_action"]


def test_stale_unknown(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 4_000_000.0
    eng.ingest_obj(pkt(1, 1, roll=0.2), received_at=t0)
    snap = eng.snapshot(now=t0 + 6.0)
    assert snap["nodes"]["1"]["status"] == STATUS_UNKNOWN


def test_duplicates_do_not_refresh(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 5_000_000.0
    p = pkt(1, 9, roll=0.2)
    eng.ingest_obj(p, received_at=t0)
    eng.ingest_obj(p, received_at=t0 + 1.0)
    assert eng.nodes[1].duplicates == 1
    assert eng.nodes[1].last.received_at == t0


def test_bad_schema_dropped(tmp_path):
    eng = engine_sim(tmp_path)
    eng.ingest_obj({"type": "telemetry", "schema": 99, "node_id": 1, "seq": 1})
    assert eng.dropped >= 1
    assert eng.nodes[1].seen is False


def test_sensor_fault_not_normal(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 6_000_000.0
    for i in range(4):
        eng.ingest_obj(pkt(1, i + 1, roll=None, pitch=None, vib=None, adc=None, valid=0), received_at=t0 + i)
    assert eng.nodes[1].status == STATUS_UNKNOWN


def test_inspection_done_closes_recovered_latches(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 3_100_000.0
    for i in range(4):
        eng.ingest_obj(pkt(1, i + 1, roll=7.0), received_at=t0 + i)
        eng.ingest_obj(pkt(2, i + 1, roll=7.0), received_at=t0 + i)
    assert eng.nodes[1].latched_alert is True
    assert eng.nodes[2].latched_alert is True
    ok, msg = eng.inspection_done()
    assert ok is False
    assert "threshold" in msg.lower()
    assert eng.nodes[1].latched_alert is True
    for i in range(4, 10):
        eng.ingest_obj(pkt(1, i + 1, roll=0.1), received_at=t0 + i)
        eng.ingest_obj(pkt(2, i + 1, roll=0.1), received_at=t0 + i)
    assert eng.nodes[1].status == STATUS_NORMAL
    assert eng.nodes[1].latched_alert is True
    ok, msg = eng.inspection_done()
    assert ok is True
    assert "closed" in msg.lower()
    assert eng.nodes[1].latched_alert is False
    assert eng.nodes[2].latched_alert is False
    snap = eng.snapshot(now=t0 + 10)
    assert snap["system_status"] == STATUS_NORMAL


def test_inspection_done_api_clears_both_nodes(tmp_path):
    app, eng = create_app("simulate", db_path=tmp_path / "web.db")
    t0 = 3_200_000.0
    for i in range(4):
        eng.ingest_obj(pkt(1, i + 1, roll=7.0), received_at=t0 + i)
        eng.ingest_obj(pkt(2, i + 1, roll=7.0), received_at=t0 + i)
    for i in range(4, 10):
        eng.ingest_obj(pkt(1, i + 1, roll=0.1), received_at=t0 + i)
        eng.ingest_obj(pkt(2, i + 1, roll=0.1), received_at=t0 + i)
    client = app.test_client()
    response = client.post("/api/inspection-done", json={})
    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert eng.nodes[1].latched_alert is False
    assert eng.nodes[2].latched_alert is False


def test_node_b_does_not_clear_node_a(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 7_000_000.0
    for i in range(4):
        eng.ingest_obj(pkt(1, i + 1, roll=7.0), received_at=t0 + i)
        eng.ingest_obj(pkt(2, i + 1, roll=0.1), received_at=t0 + i)
    assert eng.nodes[1].latched_alert is True
    for i in range(4, 10):
        eng.ingest_obj(pkt(2, i + 1, roll=0.1), received_at=t0 + i)
    assert eng.nodes[1].latched_alert is True


def test_watch_threshold(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 8_000_000.0
    for i in range(4):
        eng.ingest_obj(pkt(1, i + 1, roll=3.4), received_at=t0 + i)
    assert eng.nodes[1].status == STATUS_WATCH


def test_forecast_label_not_collapse(tmp_path):
    eng = engine_sim(tmp_path)
    t0 = 9_000_000.0
    for i in range(20):
        eng.ingest_obj(pkt(1, i + 1, roll=0.1 + i * 0.01), received_at=t0 + i)
    snap = eng.snapshot(now=t0 + 20)
    lab = snap["forecast"]["1"]["label"]
    assert "collapse" in lab.lower()
    assert "not" in lab.lower()


def test_parse_rejects_rover_as_node():
    with pytest.raises(ValueError):
        parse_telemetry({"type": "telemetry", "schema": 1, "node_id": 9, "seq": 1, "valid": 0}, 0.0)
