from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from anomaly import MIN_TRAIN, NodeAnomaly
from app import create_app
from database import Database
from engine import Engine
from forecast import SeriesForecast
from simulate import SimulatedRover
from rover_sense import explain_ir


def packet(node_id: int, seq: int, uptime_ms: int | None = None) -> dict:
    return {
        "type": "telemetry",
        "schema": 1,
        "node_id": node_id,
        "seq": seq,
        "uptime_ms": uptime_ms if uptime_ms is not None else seq * 1000,
        "valid": 7 if node_id == 1 else 5,
        "roll_deg": 0.1,
        "pitch_deg": 0.05,
        "vibration_g": 0.004,
        "adc_raw": 400 if node_id == 1 else None,
    }


def test_monitoring_and_rover_pages_are_separate(tmp_path):
    app, _ = create_app("simulate", db_path=tmp_path / "web.db")
    client = app.test_client()
    monitoring = client.get("/monitoring")
    rover = client.get("/rover")
    assert monitoring.status_code == 200
    assert rover.status_code == 200
    assert b"Monitoring &amp; AI" in monitoring.data
    assert b"Drive controls" not in monitoring.data
    assert b"Rehearsal" in monitoring.data
    assert b"scenarioPanel" not in monitoring.data
    assert b"Drive controls" in rover.data
    assert b"Isolation Forest" not in rover.data
    assert b"does not stop the motors" in rover.data
    assert b"GPIO19" in rover.data


def test_api_rejects_bad_node_and_calibration(tmp_path):
    app, _ = create_app("simulate", db_path=tmp_path / "web.db")
    client = app.test_client()
    assert client.post("/api/baseline", json={"node_id": 7}).status_code == 400
    response = client.post(
        "/api/calibration",
        json={"adc0": 100, "adc1": 100, "mm0": 0, "mm1": 10},
    )
    assert response.status_code == 400
    assert b"different" in response.data


def test_simulated_rover_has_safe_contract():
    rover = SimulatedRover()
    assert rover.command("forward")["ok"] is True
    data = rover.telemetry(100.0)
    assert data["device_id"] == "rover"
    assert data["driving"] is True
    assert isinstance(data["mq7_raw"], int)
    assert "ppm" not in data
    rover.command("stop")
    assert rover.telemetry(101.0)["driving"] is False
    rover.command("forward")
    saw_flag = False
    saw_clear = False
    for i in range(50):
        rover.command("forward")
        sample = rover.telemetry(200.0 + i)
        if sample["ir_obstacle"]:
            saw_flag = True
            assert sample["distance_cm"] < 12.0
        else:
            saw_clear = True
    assert saw_flag and saw_clear


def test_ir_is_a_flag_not_a_brake():
    near = explain_ir(9.0, True, driving=True)
    assert near["stops_motors"] is False
    assert near["is_range"] is False
    assert near["pin"] == 19
    assert near["active_level"] == "LOW"
    assert "STOP" in near["drive_note"]
    false_trip = explain_ir(80.0, True)
    assert false_trip["agreement"] == "ir_only"
    sonar_only = explain_ir(8.0, False)
    assert sonar_only["agreement"] == "sonar_only"
    clear = explain_ir(40.0, False)
    assert clear["agreement"] == "clear"


def test_ridge_forecast_reports_holdout_error_and_eta():
    forecast = SeriesForecast("tilt change", "deg", 3.0, 6.0)
    for i in range(45):
        forecast.push(0.15 + i * 0.09 + 0.01 * math.sin(i), float(i))
    result = forecast.predict()
    assert result["state"] == "READY"
    assert "sklearn" in result["model"].lower() or result["selected"] in {
        "Ridge", "HuberRegressor", "LinearRegression",
    }
    assert result["selected"] in {"Ridge", "HuberRegressor", "LinearRegression"}
    assert result["candidates"]
    assert len(result["points"]) == 30
    assert len(result["lower"]) == 30
    assert result["mae"] is not None
    assert result["seconds_to_alert"] is not None
    assert "not a collapse" in result["label"].lower()


def test_flat_forecast_has_no_time_to_threshold():
    forecast = SeriesForecast("tilt change", "deg", 3.0, 6.0)
    for i in range(40):
        forecast.push(0.2, float(i))
    result = forecast.predict()
    assert result["state"] == "READY"
    assert result["seconds_to_watch"] is None
    assert result["seconds_to_alert"] is None
    assert min(result["points"]) >= 0


def test_isolation_forest_trains_persists_and_flags_outlier(tmp_path):
    model = NodeAnomaly(1, tmp_path, load_existing=False)
    names = ["tilt_change_deg", "vibration_g", "d_tilt", "relative_mm"]
    rng = np.random.default_rng(0)
    for _ in range(MIN_TRAIN):
        row = [
            float(rng.normal(0.15, 0.02)),
            float(rng.normal(0.004, 0.0005)),
            float(rng.normal(0.0, 0.01)),
            float(rng.normal(0.0, 0.03)),
        ]
        model.note_healthy(row, names)
    ok, _ = model.can_train(live=True, latched_or_watch=False)
    assert ok is True
    model.train("test-time")
    assert model.path.exists()
    unusual = model.score_row([7.0, 0.2, 1.0, 5.0], names)
    assert unusual.state == "UNUSUAL"
    assert unusual.top_feature in names
    assert unusual.isolation_state == "UNUSUAL"
    assert any("LocalOutlierFactor" in name for name in unusual.models)

    loaded = NodeAnomaly(1, tmp_path)
    assert loaded.n_train == MIN_TRAIN
    assert loaded.trained_at == "test-time"


def test_live_calibration_and_baseline_persist(tmp_path):
    path = tmp_path / "persist.db"
    first_db = Database(path)
    first = Engine("live", first_db)
    first.set_calibration(400, 3600, 0, 20)
    first.ingest_obj(packet(1, 1), received_at=100.0)
    assert first.capture_baseline(1).startswith("Baseline captured")
    first_db.close()

    second_db = Database(path)
    second = Engine("live", second_db)
    assert second.crack_calibrated() is True
    assert second.nodes[1].roll0 == 0.1
    assert second.nodes[1].pitch0 == 0.05
    second_db.close()


def test_packet_gap_out_of_order_and_reboot(tmp_path):
    engine = Engine("simulate", Database(tmp_path / "seq.db"))
    engine.ingest_obj(packet(2, 10), received_at=10.0)
    engine.ingest_obj(packet(2, 13), received_at=11.0)
    assert engine.nodes[2].packets_lost == 2

    stale = packet(2, 12, uptime_ms=14_000)
    engine.ingest_obj(stale, received_at=12.0)
    assert engine.nodes[2].out_of_order == 1
    assert engine.nodes[2].last_seq == 13

    reboot = packet(2, 1, uptime_ms=500)
    engine.ingest_obj(reboot, received_at=13.0)
    assert engine.nodes[2].last_seq == 1
    assert any(event["kind"] == "reboot" for event in engine.db.recent_events())


def test_seeded_simulate_fits_in_memory_anomaly_models(tmp_path):
    engine = Engine("simulate", Database(tmp_path / "seed.db"))
    engine.seed_simulated_history(40)
    snap = engine.snapshot()
    assert snap["scenario"] == "normal"
    assert snap["forecast"]["1"]["tilt"]["state"] == "READY"
    assert len(snap["forecast"]["1"]["tilt"]["points"]) == 30
    assert snap["ai"]["1"]["state"] in ("READY", "UNUSUAL")
    assert snap["ai"]["1"]["can_train"] is False
    assert snap["ai"]["1"]["n_train"] >= 36
    assert snap["ai"]["1"]["prior"] is True or snap["ai"]["1"]["simulated"] is True
    assert snap["joint"]["model"].startswith("sklearn IsolationForest")
    ok, msg = engine.train(1)
    assert ok is False
    assert "simulated" in msg.lower()
    assert engine.anomaly[1].forest is not None


def test_anomaly_unusual_cannot_clear_rule_latch(tmp_path):
    engine = Engine("simulate", Database(tmp_path / "latch.db"))
    engine.seed_simulated_history(40)
    start = (engine.nodes[1].last_seq or 0) + 1
    t0 = 30_000.0
    for i in range(4):
        body = packet(1, start + i)
        body["roll_deg"] = 7.0
        engine.ingest_obj(body, received_at=t0 + i)
        engine.ingest_obj(packet(2, start + i), received_at=t0 + i)
    assert engine.nodes[1].latched_alert is True
    snap = engine.snapshot(now=t0 + 4)
    assert snap["nodes"]["1"]["latched_alert"] is True
    assert snap["system_status"] == "ALERT"


def test_monitoring_shows_prediction_and_node_b_actions(tmp_path):
    app, _ = create_app("simulate", db_path=tmp_path / "web.db")
    client = app.test_client()
    html = client.get("/monitoring").data
    assert b"predictionRows" in html
    assert b'data-action="ack" data-node="2"' in html
    assert b'data-action="clear" data-node="2"' in html
    assert b"Drive controls" not in html
    assert b"AIML stack" in html
    assert b"Inspection done" in html
    rover = client.get("/rover").data
    assert b"How to drive" in rover
    assert b"Inspection done" in rover
    assert b"Isolation Forest" not in rover
    assert b"predictionRows" not in rover


def test_helper_faq_is_local_and_warns(tmp_path):
    from helper import answer_question
    from app import create_app

    collapse = answer_question("Will the roof collapse? Give me a probability.", allow_llm=False)
    assert collapse["llm"] is False
    assert collapse["warn"] is True
    assert "probability" in collapse["answer"].lower()
    assert "not" in collapse["answer"].lower()

    flash = answer_question("how do I put the code on the hardware", allow_llm=False)
    assert flash["topic"] == "flash"
    assert "Arduino" in flash["answer"]
    assert "node.ino" in flash["answer"]

    ppm = answer_question("what is the CO ppm?", allow_llm=False)
    assert ppm["warn"] is True
    assert "raw" in ppm["answer"].lower()

    rover = answer_question("does IR stop the motors?", allow_llm=False)
    assert rover["topic"] == "ir"
    assert "does not" in rover["answer"].lower()

    app, _ = create_app("simulate", db_path=tmp_path / "web.db")
    client = app.test_client()
    posted = client.post("/api/helper", json={"question": "What is MOLE?"})
    assert posted.status_code == 200
    body = posted.get_json()
    assert body["llm"] is False
    assert "SIH26025" in body["answer"]
    assert (ROOT / "helper_handbook.md").is_file()
    openq = answer_question("write a one-line thank-you to a mentor for tonight's lab", allow_llm=False)
    assert openq["ok"] is True
    assert "helper" in openq["answer"].lower()
    assert "I only answer MOLE" not in openq["answer"]
    mathq = answer_question("What is 2 plus 2?", allow_llm=False)
    assert "4" in mathq["answer"]
    monitoring = client.get("/monitoring").data
    rover_page = client.get("/rover").data
    assert b"/assets/helper.js" in monitoring
    assert b"/assets/helper.js" in rover_page
    assert b"Drive controls" not in monitoring


def test_helper_mistral_uses_api_key(tmp_path, monkeypatch):
    import helper

    class FakeResp:
        status_code = 200
        headers = {}

        def json(self):
            return {"choices": [{"message": {"content": "Node A MPU is GPIO21/22."}}]}

    monkeypatch.setenv("MOLE_HELPER_LLM_TEST", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key-not-real")
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-small-latest")
    monkeypatch.setattr(helper.requests, "post", lambda *args, **kwargs: FakeResp())

    status = helper.helper_status()
    assert status["llm"] is True
    assert status["provider"] == "mistral"

    result = helper.ask_llm("Why would a judge confuse rover IMU with Node B?", {})
    assert result is not None
    assert "GPIO21" in result["answer"]
    assert result["model"] == "mistral-small-latest"


def test_shipped_prior_models_are_ready_and_flag_outliers():
    from engine import ARTIFACTS

    model = NodeAnomaly(1, ARTIFACTS)
    assert model.prior is True
    assert model.forest is not None
    quiet = model.score_row([0.18, 0.0045, 0.0, 0.15], model.names)
    assert quiet.state == "READY"
    unusual = model.score_row([7.0, 0.2, 1.0, 5.0], model.names)
    assert unusual.state == "UNUSUAL"
