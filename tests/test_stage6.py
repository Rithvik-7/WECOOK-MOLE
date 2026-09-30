import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from analysis import classify_window
from evaluate import assign_partitions, evaluate, forecast, locked_baseline, windows


def samples(values, session="s"):
    return [{"tilt_deg": v, "valid": True, "origin": "simulated", "session_id": session, "sequence": i, "sample_time": f"2026-09-27T10:{i:02d}:00+00:00"} for i, v in enumerate(values)]


def test_shadow_does_not_change_the_warning_or_invent_a_score():
    result = classify_window(samples([0, 0.02, 0, 1.3, 1.6, 1.9]), [])
    assert result["condition"] == "movement"
    assert result["score"] is None
    assert result["shadow"]["affects_warning"] is False
    assert result["shadow"]["isolation_forest"] == "unavailable"
    assert result["compared"]["isolation_forest"] is None
    assert result["forecast"]["available"] is False
    assert result["forecast"]["displacement_deg"] is None
    assert "danger" not in result


def test_open_incident_keeps_the_stored_baseline():
    assert locked_baseline(0.2, True, 1.9) == 0.2
    assert locked_baseline(0.2, False, 0.25) == 0.25


def test_sessions_are_split_before_windows():
    records = []
    for session, day in (("early", "01"), ("late", "02")):
        for node in ("A", "B"):
            records.append({"session_id": session, "node_id": node, "sample_time": f"2026-09-{day}T00:00:00+00:00"})
    train, test = assign_partitions(records)
    assert train == {"early"}
    assert test == {"late"}
    early = samples([0, 0.1, 0.2, 0.3, 0.4], "early")
    made = windows(early, size=3, step=2)
    assert made
    assert all(row["session_id"] == "early" for window in made for row in window)


def test_evaluation_needs_a_held_out_session():
    one = [{"session_id": "only", "samples": samples([0, 0, 0, 0, 0, 0]), "label": "normal"}]
    assert evaluate(one)["available"] is False
    two = [
        {"session_id": "early", "samples": samples([0, 0, 0, 0, 0, 0]), "label": "normal"},
        {"session_id": "late", "samples": [{"tilt_deg": v, "valid": True, "sample_time": f"2026-10-01T00:{i:02d}:00+00:00"} for i, v in enumerate([0, 0.02, 0, 1.3, 1.6, 1.9])], "label": "movement"},
    ]
    report = evaluate(two)
    assert report["available"] is True
    assert report["test_sessions"] == ["late"]
    assert report["missed_events"] == 0
    assert report["false_alarms"] == 0
    assert forecast(30)["displacement_deg"] is None
