"""Session-level evaluation. It does not train a model or change warnings."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from analysis import classify_window


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("sample_time needs a timezone")
    return parsed


def assign_partitions(records: list[dict]) -> tuple[set[str], set[str]]:
    """Keep every node from one session together. Earlier sessions train. Later sessions are held out."""
    groups: dict[str, list[dict]] = {}
    for record in records:
        groups.setdefault(record["session_id"], []).append(record)
    ordered = sorted(groups, key=lambda session: min(_time(item["sample_time"]) for item in groups[session]))
    if len(ordered) < 2:
        return set(ordered), set()
    cut = max(1, len(ordered) // 2)
    if cut >= len(ordered):
        cut = len(ordered) - 1
    return set(ordered[:cut]), set(ordered[cut:])


def windows(samples: list[dict], size: int = 4, step: int = 2) -> list[list[dict]]:
    if size < 2 or step < 1 or len(samples) < size:
        return []
    return [samples[i : i + size] for i in range(0, len(samples) - size + 1, step)]


def locked_baseline(stored, incident_open: bool, proposed):
    if incident_open:
        return stored
    return proposed


def forecast(horizon_min: int) -> dict:
    return {
        "available": False,
        "horizon_min": horizon_min,
        "displacement_deg": None,
        "reason": "No held-out horizon evaluation. No displacement is produced.",
    }


def similar_events(labelled: list[dict]) -> list[dict]:
    if not labelled:
        return []
    return [{"session_id": item["session_id"], "label": item["label"]} for item in labelled[:5]]


def evaluate(sessions: list[dict]) -> dict:
    """sessions items need session_id, node_id, samples, and label movement or normal."""
    train, test = assign_partitions(
        [{"session_id": item["session_id"], "sample_time": item["samples"][0]["sample_time"]} for item in sessions if item.get("samples")]
    )
    report = {
        "available": False,
        "missed_events": None,
        "false_alarms": None,
        "detection_delay_samples": None,
        "train_sessions": sorted(train),
        "test_sessions": sorted(test),
        "reason": "Need at least two sessions so one can be held out.",
        "scope": "This is not field accuracy and not a probability of collapse.",
    }
    if not test:
        return report
    missed = 0
    false_alarms = 0
    delays = []
    for item in sessions:
        if item["session_id"] not in test:
            continue
        states = [classify_window(item["samples"][: i + 1], [])["condition"] for i in range(len(item["samples"]))]
        final = states[-1]
        if item["label"] == "movement":
            if final != "movement":
                missed += 1
                delays.append(None)
            else:
                delays.append(next(i for i, state in enumerate(states) if state == "movement"))
        elif item["label"] == "normal" and final == "movement":
            false_alarms += 1
    known = [item for item in delays if item is not None]
    report.update(
        available=True,
        missed_events=missed,
        false_alarms=false_alarms,
        detection_delay_samples=None if not known else round(sum(known) / len(known), 2),
        reason="Held-out sessions only. Rules were not replaced.",
    )
    return report
