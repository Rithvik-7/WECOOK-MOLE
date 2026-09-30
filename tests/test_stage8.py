from datetime import datetime, timedelta, timezone
from test_flow import client

HEADERS = {"X-Mole-Capability": "test-token"}


def incident_id():
    state = client.get("/api/state").json()
    return state["incidents"][0]["id"]


def test_mission_links_evidence_without_driving():
    target = incident_id()
    assert client.post("/api/missions", json={"incident_id": target, "note": "Look at the surface crack candidate."}).status_code == 403
    first = client.post("/api/missions", json={"incident_id": target, "note": "Look at the surface crack candidate."}, headers=HEADERS)
    assert first.status_code == 200
    body = first.json()
    assert body["unit"] == "R1" and body["drive"] == "not enabled"
    mission = body["id"]
    evidence = client.post(f"/api/missions/{mission}/evidence", json={"note": "A mark was seen. No size is inferred.", "finding": "Reviewed candidate."}, headers=HEADERS)
    assert evidence.status_code == 200 and evidence.json()["dimensions_inferred"] is False
    assert client.post(f"/api/missions/{mission}/position", json={"known": True, "note": "Guessed coordinates"}, headers=HEADERS).status_code == 409
    recorded = client.post(f"/api/missions/{mission}/position", json={"known": False, "note": "Last contact unavailable"}, headers=HEADERS)
    assert recorded.json()["inspection_complete"] is True
    detail = client.get(f"/api/missions/{mission}").json()
    assert detail["distinct_from"] == "Node C"
    assert detail["position"]["known"] is False
    assert detail["camera"] == "not equipped"
    second = client.post("/api/missions", json={"incident_id": target, "note": "Repeat visit after the first note."}, headers=HEADERS).json()
    assert mission in second["previous_mission_ids"]
    related = client.get(f"/api/missions/{second['id']}").json()["same_node_mission_ids"]
    assert mission in related


def test_future_drive_and_lost_link_do_not_move_the_rover():
    mission = client.post("/api/missions", json={"incident_id": incident_id(), "note": "Controller check only."}, headers=HEADERS).json()["id"]
    later = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    denied = client.post("/api/commands", json={"mission_id": mission, "kind": "forward", "expires_at": later}, headers=HEADERS)
    assert denied.status_code == 409
    lost = client.post(f"/api/missions/{mission}/link-lost", headers=HEADERS)
    assert lost.status_code == 200 and lost.json()["executed"] is False
    assert "No vehicle stop" in lost.json()["note"]
