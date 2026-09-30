"""Versioned prototype analysis. Statistical descriptors are not a trained model."""
from __future__ import annotations
from datetime import datetime
from math import isfinite
from statistics import median

RULE_VERSION = "prototype-window-v2"
MOVEMENT_DEG = 1.2
WATCH_DEG = 0.6
SUSTAINED_SAMPLES = 3

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)

def robust_z(value: float, baseline: list[float]) -> float | None:
    clean = [v for v in baseline if number(v)]
    if len(clean) < 3 or not number(value):
        return None
    center = median(clean)
    mad = median(abs(v - center) for v in clean)
    # A zero-spread baseline cannot establish a reliable normalized deviation.
    return None if mad < 1e-9 else .67448975 * (value - center) / mad

def change_point(series: list[float]) -> dict | None:
    if len(series) < 6:
        return None
    split = len(series) // 2
    shift = median(series[split:]) - median(series[:split])
    return {"split_index": split, "shift": round(shift, 4), "method": "median-window-shift"} if abs(shift) >= .4 else None

def time_seconds(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None

def classify_window(samples: list[dict], neighbors: list[dict], commissioned_baseline: float | None = None) -> dict:
    samples = samples[-120:]
    latest = samples[-1] if samples else {}
    usable = [s for s in samples if s.get("valid", True) and number(s.get("tilt_deg"))]
    tilts = [s["tilt_deg"] for s in usable]
    total = len(samples)
    quality = {"total_count": total, "valid_count": len(usable), "coverage_pct": round(100 * len(usable) / total, 1) if total else 0,
               "freshness": "stale" if latest.get("stale") else "recorded-demo" if latest.get("origin") == "simulated" else "source-reported",
               "latest_valid": latest.get("valid", False) and number(latest.get("tilt_deg"))}
    evidence = []
    related = []
    movement = "unavailable"
    gas = "unavailable"
    fault = bool(latest.get("fault")) or bool(samples and (not latest.get("valid", True) or not number(latest.get("tilt_deg"))))
    features = {"baseline_deg": None, "delta_deg": None, "robust_z": None, "slope_deg_min": None, "duration_min": None, "sustained_samples": 0, "window_shift_deg": None}
    if len(tilts) >= 3:
        baseline = commissioned_baseline if number(commissioned_baseline) else median(tilts[:3])
        difference = tilts[-1] - baseline
        direction = 1 if difference >= 0 else -1
        # Only consecutive valid samples can satisfy persistence. Gaps reset it.
        sustained = 0
        # Preserve evidence from the last valid window if the newest channel faults.
        tail = list(samples)
        while tail and (not tail[-1].get("valid", True) or not number(tail[-1].get("tilt_deg"))):
            tail.pop()
        previous_sequence = None
        for s in reversed(tail):
            sequence = s.get("sequence")
            if previous_sequence is not None and sequence is not None and previous_sequence - sequence != 1:
                break
            previous_sequence = sequence
            if not s.get("valid", True) or not number(s.get("tilt_deg")):
                break
            if direction * (s["tilt_deg"] - baseline) + 1e-8 < MOVEMENT_DEG:
                break
            sustained += 1
        movement = "movement" if len(tilts) >= 6 and sustained >= SUSTAINED_SAMPLES else "watch" if abs(difference) >= WATCH_DEG else "normal"
        vibration = [s.get("vibration") for s in usable[-3:] if number(s.get("vibration"))]
        if movement == "normal" and vibration and max(vibration) >= 2.5:
            movement = "watch"
            evidence.append("Recent vibration is elevated without sustained tilt change. The physical cause is unclassified.")
        features.update(baseline_deg=round(baseline,4), delta_deg=round(difference,4), robust_z=robust_z(tilts[-1],tilts[:3]), sustained_samples=sustained)
        point = change_point(tilts)
        if point:
            features["window_shift_deg"] = point["shift"]
        if movement == "movement":
            evidence.insert(0,f"{sustained} consecutive valid observations exceed the prototype {MOVEMENT_DEG}° change criterion in the same direction.")
        elif movement == "watch":
            evidence.insert(0,f"Latest tilt differs from the reference by {difference:+.2f}°. Sustained movement is not yet established by this window.")
        else:
            evidence.insert(0,f"Tilt differs by {difference:+.2f}° from the window reference; no configured tilt warning is detected.")
        if number(commissioned_baseline):
            evidence.append(f"Reference {baseline:.2f}° is the active operator-recorded baseline. Confirm the instrument and mounting after any physical change.")
        else:
            evidence.append(f"Reference {baseline:.2f}° is the median of the first three valid observations in this window. It is not a surveyed commissioning baseline.")
        times=[time_seconds(s.get("sample_time")) for s in usable]
        if all(t is not None for t in times) and all(b>a for a,b in zip(times,times[1:])):
            duration=(times[-1]-times[0])/60
            features["duration_min"]=round(duration,2)
            slopes=[(tilts[j]-tilts[i])/((times[j]-times[i])/60) for i in range(len(tilts)) for j in range(i+1,len(tilts))]
            features["slope_deg_min"]=round(median(slopes),5)
            evidence.append(f"The robust tilt trend is {features['slope_deg_min']:+.3f}°/min across {duration:.1f} minutes of observations.")
        else:
            evidence.append("Time-based trend rate is unavailable: timestamps must be valid and strictly increasing.")
        if point:
            evidence.append(f"The median shifted by {point['shift']:+.2f}° between the two halves of the window. This is a descriptive change signal.")
        related=[n["node_id"] for n in neighbors if n.get("valid") and n.get("condition")=="movement"]
        if movement=="movement":
            evidence.append("Other surface observations also show movement: "+", ".join(related)+". Timing and physical association require review." if related else "The local movement remains visible without requiring a neighbouring-node vote.")
    else:
        evidence.append("At least three valid tilt observations are needed for a window reference.")
    if number(latest.get("gas_raw")):
        gas = "warmup" if not latest.get("gas_ready") else "gas" if latest["gas_raw"]>=1800 else "normal"
        if gas=="gas":
            evidence.append(f"A separate MQ-2 raw-signal rule is active at {latest['gas_raw']:g}. This is not gas concentration.")
        elif gas=="warmup":
            evidence.append("MQ-2 warm-up is incomplete. Gas interpretation is unavailable.")
    if fault:
        evidence.append(latest.get("fault_reason") or "Latest tilt channel is invalid. Previous movement evidence is retained; recovery is not inferred.")
    if latest.get("stale"):
        evidence.append("Latest physical data is stale. Its previous movement evidence is retained, with no claim of current normality.")
    condition = "movement" if movement=="movement" else "gas" if gas=="gas" else "sensor_fault" if fault else "stale" if latest.get("stale") else movement
    return {"condition":condition,"movement_state":movement,"gas_state":gas,"fault_active":fault,"evidence":evidence,"summary":evidence[0],"features":features,"quality":quality,"score":None,
            "model":"rules-robust-window-trends","rule_version":RULE_VERSION,"reference_source":"commissioned" if number(commissioned_baseline) else "window", "model_state":"No trained artifact loaded. Window statistics and laboratory rules only.",
            "compared":{"rules":movement,"robust_z":features.get("robust_z"),"change_point_deg":features.get("window_shift_deg"),"isolation_forest":None,"neighbours":related},
            "shadow":{"isolation_forest":"unavailable","affects_warning":False,"reason":"No saved model artifact. Rules remain the only operational warning."},
            "forecast":{"available":False,"horizon_min":None,"displacement_deg":None,"reason":"No held-out horizon evaluation."}}
