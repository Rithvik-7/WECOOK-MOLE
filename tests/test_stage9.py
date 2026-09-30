import json
from test_flow import client

HEADERS = {"X-Mole-Capability": "test-token"}
SHEET = "node_id,sample_time,channel,value,unit\nA,2019-01-01T00:00:00+00:00,tilt_deg,0.2,deg\nA,2019-01-01T00:10:00+00:00,tilt_deg,unavailable,deg\n"


def test_history_csv_and_one_page_report():
    history = client.get("/api/history", params={"node_id": "A", "channel": "tilt_deg", "limit": 3}).json()
    assert history["original_count"] >= history["returned_count"]
    assert history["points"][0]["unit"] == "deg"
    csv_body = client.get("/api/exports/telemetry.csv").text
    assert "tilt_deg" in csv_body and ",deg" in csv_body
    assert client.get("/api/exports/telemetry.xlsx").content[:2] == b"PK"
    from main import render_report_pdf
    pdf = render_report_pdf({
        "id": "RPT-STAGE9-R1",
        "revision": 1,
        "snapshot": json.dumps({
            "id": "INC-A-TEST", "node_id": "A", "status": "CLOSED", "severity": "watch",
            "opened_at": "2019-01-01T00:00:00+00:00", "updated_at": "2019-01-01T01:00:00+00:00",
            "explanation": "A short watch explanation.", "origin": "simulated", "closure_reason": "Reviewed.",
            "actions": [{"action": "CLOSED", "at": "2019-01-01T01:00:00+00:00"}],
            "telemetry": [{"tilt_deg": 0.2}, {"tilt_deg": 0.4}, {"tilt_deg": 0.3}],
            "mission": None,
        }),
    })
    assert pdf.startswith(b"%PDF") and b"/Count 1" in pdf


def test_import_preview_blocks_bad_time_and_keeps_the_source():
    bad = client.post("/api/imports/preview", json={"filename": "bad.csv", "csv_text": "node_id,sample_time,channel,value,unit\nA,2019-01-01T00:00:00,tilt_deg,1,deg\n"}).json()
    assert bad["issues"]
    assert client.post(f"/api/imports/{bad['id']}/commit", headers=HEADERS).status_code == 409
    preview = client.post("/api/imports/preview", json={"filename": "old.csv", "csv_text": SHEET}).json()
    assert preview["issues"] == [] and preview["source_kept"] is True
    stored = client.post(f"/api/imports/{preview['id']}/commit", headers=HEADERS)
    assert stored.status_code == 200 and stored.json()["origin"] == "imported"
    assert client.post(f"/api/imports/{preview['id']}/commit", headers=HEADERS).status_code == 409
    node = next(item for item in client.get("/api/state").json()["nodes"] if item["id"] == "A")
    assert node["latest"]["session_id"] == "seed"
    assert node["latest"]["potentiometer_mm"] is None
