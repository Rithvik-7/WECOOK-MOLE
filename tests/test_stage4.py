import json
import os
import sqlite3

from test_flow import client

HEADERS = {"X-Mole-Capability": "test-token"}


def test_old_packet_is_stored_apart_from_its_feature():
    saved = client.post("/api/telemetry", json={
        "node_id": "A",
        "session_id": "stage4-old",
        "sequence": 0,
        "origin": "simulated",
        "sample_time": "2020-06-01T00:00:00+00:00",
        "tilt_deg": 0.41,
        "vibration": 0.2,
        "potentiometer_raw": 400,
        "valid": True,
    })
    assert saved.status_code == 200 and saved.json()["stored"] is True
    conn = sqlite3.connect(os.environ["MOLE_DB"])
    conn.row_factory = sqlite3.Row
    payload = json.loads(conn.execute("SELECT payload FROM telemetry WHERE session_id='stage4-old'").fetchone()["payload"])
    assert payload["tilt_deg"] == 0.41
    assert payload["potentiometer_mm"] is None
    assert "condition" not in payload
    feature = json.loads(conn.execute("SELECT result FROM features WHERE session_id='stage4-old'").fetchone()["result"])
    assert "condition" in feature
    conn.close()
    reopened = sqlite3.connect(os.environ["MOLE_DB"])
    assert reopened.execute("SELECT COUNT(*) FROM telemetry WHERE session_id='stage4-old'").fetchone()[0] == 1
    reopened.close()
    node = next(item for item in client.get("/api/state").json()["nodes"] if item["id"] == "A")
    assert node["latest"]["session_id"] == "seed"
    assert node["latest"]["potentiometer_mm"] is None


def test_failed_job_stays_visible_and_retry_does_not_duplicate_success():
    failed = client.post("/api/jobs", json={"kind": "report_file", "report_id": "missing-report"}).json()
    assert failed["status"] == "FAILED" and failed["attempts"] == 1
    retried = client.post(f"/api/jobs/{failed['id']}/retry").json()
    assert retried["status"] == "FAILED" and retried["attempts"] == 2
    listed = client.get("/api/jobs").json()["jobs"]
    assert sum(item["id"] == failed["id"] for item in listed) == 1
    exported = client.post("/api/jobs", json={"kind": "telemetry_export"}).json()
    assert exported["status"] == "SUCCEEDED" and exported["attempts"] == 1
    download = client.get(f"/api/jobs/{exported['id']}/file")
    assert download.status_code == 200 and download.content[:2] == b"PK"
    assert client.post(f"/api/jobs/{exported['id']}/retry").status_code == 409
    state = client.get("/api/state").json()
    assert state["weather"]["observed_rain_mm"] is None
    assert state["weather"]["freshness"] == "unavailable"
    assert state["persistence"]["features_kept_separate"] is True
    assert state["persistence"]["jobs_failed"] >= 1


def test_calibration_and_sync_do_not_rewrite_readings():
    assert client.post("/api/calibrations", json={"node_id": "A", "channel": "potentiometer_raw", "note": "Mount not calibrated"}).status_code == 403
    saved = client.post("/api/calibrations", json={"node_id": "A", "channel": "potentiometer_raw", "note": "Mount not calibrated"}, headers=HEADERS)
    assert saved.status_code == 200 and saved.json()["readings_changed"] is False
    note = client.get("/api/calibrations").json()
    assert note["records"][0]["channel"] == "potentiometer_raw"
    assert "millimetres" in note["effect"]
    sync = client.post("/api/sync-jobs", json={"source": "gateway", "sent": 2, "pending": 1, "rejected": 0})
    assert sync.status_code == 200 and sync.json()["stored"] is True
    assert client.get("/api/sync-jobs").json()["jobs"][0]["pending"] == 1
