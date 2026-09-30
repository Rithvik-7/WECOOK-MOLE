import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["MOLE_DB"] = str(ROOT / "data" / "test-mole.db")
os.environ["MOLE_OPERATOR_TOKEN"] = "test-token"
db = Path(os.environ["MOLE_DB"])
if db.exists():
    db.unlink()

from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(ROOT / "api"))
from main import app

client = TestClient(app)


def test_public_cannot_acknowledge():
    state = client.get("/api/state").json()
    incident = state["incidents"][0]
    denied = client.post(f"/api/incidents/{incident['id']}/acknowledge", json={"reason": "no credential"})
    assert denied.status_code == 403


def test_ingest_persists_and_targets_one_node():
    stored = client.post("/api/telemetry", json={
        "node_id": "B", "session_id": "lab", "sequence": 1, "origin": "simulated",
        "tilt_deg": 4.2, "vibration": 0.5, "valid": True,
    })
    assert stored.json()["stored"] is True
    again = client.get("/api/state").json()
    nodes = {item["id"]: item["condition"] for item in again["nodes"]}
    assert nodes["B"] == "unavailable"
    assert nodes["A"] == "normal"
    duplicate = client.post("/api/telemetry", json={
        "node_id": "B", "session_id": "lab", "sequence": 1, "origin": "simulated", "tilt_deg": 4.2,
    })
    assert duplicate.json()["duplicate"] is True


def test_close_and_expired_command():
    state = client.get("/api/state").json()
    incident = next(item for item in state["incidents"] if item["node_id"] == "B")
    headers = {"X-Mole-Capability": "test-token"}
    assert client.post(f"/api/incidents/{incident['id']}/acknowledge", json={"reason": "seen"}, headers=headers).status_code == 200
    assert client.post(f"/api/incidents/{incident['id']}/review", json={"reason": "checked"}, headers=headers).status_code == 200
    closed = client.post(f"/api/incidents/{incident['id']}/close", json={"reason": "follow-up logged"}, headers=headers)
    report = closed.json()["report_id"]
    pdf = client.get(f"/api/reports/{report}.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    workbook = client.get("/api/exports/telemetry.xlsx")
    assert workbook.status_code == 200 and workbook.content[:2] == b"PK"
    mission = client.post("/api/missions", json={"incident_id": incident["id"]}, headers=headers).json()
    expired = client.post("/api/commands", json={"mission_id": mission["id"], "kind": "forward", "expires_at": "2020-01-01T00:00:00+00:00"}, headers=headers)
    assert expired.json()["executed"] is False
