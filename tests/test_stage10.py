import io
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "firmware"))
sys.path.insert(0, str(ROOT / "scripts"))
from analysis import classify_window
from logic import Receiver, build_packet
from backup import backup, restore
from test_flow import client
from test_gateway import gateway

HEADERS = {"X-Mole-Capability": "test-token"}


def series(values, **extra):
    start = datetime(2026, 9, 27, tzinfo=timezone.utc)
    rows = []
    for index, value in enumerate(values):
        row = {"tilt_deg": value, "valid": True, "origin": "simulated", "sequence": index, "sample_time": (start + timedelta(minutes=index)).isoformat()}
        row.update(extra)
        rows.append(row)
    return rows


def test_backup_round_trip(tmp_path):
    database = tmp_path / "mole.db"
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    database.write_text("database-bytes", encoding="utf-8")
    (evidence / "note.json").write_text("{}", encoding="utf-8")
    saved = backup(database, evidence, tmp_path / "backup")
    assert saved["evidence"] == ["note.json"]
    database.unlink()
    shutil.rmtree(evidence)
    restore(tmp_path / "backup", database, evidence)
    assert database.read_text(encoding="utf-8") == "database-bytes"
    assert (evidence / "note.json").is_file()


def test_health_is_local():
    health = client.get("/health").json()
    assert health["ok"] is True
    assert health["deployment"] == "local"
    assert health["https"] is False


def test_demonstration_cases(tmp_path, monkeypatch):
    assert all(classify_window(series([0.2, 0.2, 0.21, 0.2, 0.2, 0.2]), [])["condition"] == "normal" for _ in "ABCD")
    assert classify_window(series([0, 0.02, 0, 1.3, 1.6, 1.9]), [])["condition"] == "movement"
    coordinated = classify_window(series([0, 0.02, 0, 1.3, 1.6, 1.9]), [{"node_id": "A", "condition": "movement", "valid": True}])
    assert coordinated["condition"] == "movement" and "A" in coordinated["compared"]["neighbours"]
    assert classify_window(series([0.2, 0.2, 0.2, 0.2, 0.2, 0.2], vibration=3), [])["condition"] == "watch"
    fault = series([0.2, 0.2, 0.2, 0.2, 0.2, 0.2])
    fault[-1].update(valid=False, fault=True)
    assert classify_window(fault, [])["condition"] == "sensor_fault"
    stale = series([0.2, 0.2, 0.2, 0.2, 0.2, 0.2])
    stale[-1]["stale"] = True
    assert classify_window(stale, [])["condition"] == "stale"
    assert Receiver().accept(build_packet("A", "boot", 1, {"tilt_deg": 0.2}, hops=2), 0)["reason"] == "not-a-star"

    monkeypatch.setattr(gateway, "QUEUE", tmp_path / "queue.db")
    gateway.enqueue({"sequence": 1, "sample_time": "2026-01-01T00:00:00+00:00"})
    def offline(*args, **kwargs):
        raise OSError("offline")
    monkeypatch.setattr(gateway.urllib.request, "urlopen", offline)
    assert gateway.sync()["pending"] == 1
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps({"stored": True}).encode()
    monkeypatch.setattr(gateway.urllib.request, "urlopen", lambda *args, **kwargs: Reply())
    assert gateway.sync()["sent"] == 1
    assert gateway.sync()["sent"] == 0

    assert client.post("/api/incidents/missing/acknowledge", json={"reason": "seen"}).status_code == 403
    bare = client.post("/api/sos", json={"message": "help", "request_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"})
    located = client.post("/api/sos", json={"message": "help", "lat": 23.6, "lon": 85.3, "request_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"})
    assert bare.json()["status"] == "QUEUED" and located.json()["status"] == "QUEUED"
    assert "help" not in json.dumps(client.get("/api/state").json()["sos"])

    incident = client.get("/api/state").json()["incidents"][0]["id"]
    mission = client.post("/api/missions", json={"incident_id": incident, "note": "Stage 10 inspection."}, headers=HEADERS).json()
    evidence = client.post(f"/api/missions/{mission['id']}/evidence", json={"note": "Reviewed mark.", "finding": "Candidate only."}, headers=HEADERS)
    assert evidence.status_code == 200 and evidence.json()["dimensions_inferred"] is False
    assert client.get("/api/exports/telemetry.xlsx").content[:2] == b"PK"
    assert "tilt_deg" in client.get("/api/exports/telemetry.csv").text
    from main import render_report_pdf
    pdf = render_report_pdf({"id": "RPT-STAGE10-R1", "revision": 1, "snapshot": json.dumps({"id": incident, "node_id": "B", "status": "CLOSED", "severity": "movement", "opened_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T01:00:00+00:00", "explanation": "Sustained tilt.", "origin": "simulated", "closure_reason": "Reviewed.", "actions": [], "telemetry": [{"tilt_deg": 0.2}, {"tilt_deg": 1.4}], "mission": {"id": mission["id"], "state": "EVIDENCE ATTACHED"}})})
    assert pdf.startswith(b"%PDF") and b"/Count 1" in pdf
    assert Path(ROOT / "docs" / "OPERATIONS.md").is_file()
