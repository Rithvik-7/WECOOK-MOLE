"""Honest rover IR vs ultrasonic notes. IR is a digital flag, not ranging."""

from __future__ import annotations

from typing import Any, Optional

# Cheap digital IR modules are typically useful inside ~8–20 cm, not HC-SR04 range.
IR_USEFUL_CM = 12.0
SONAR_CLOSE_CM = 25.0
SONAR_VERY_CLOSE_CM = 15.0


def explain_ir(
    distance_cm: Optional[float],
    ir_obstacle: Optional[bool],
    *,
    simulated: bool = False,
    driving: bool = False,
) -> dict[str, Any]:
    flagged: Optional[bool]
    if ir_obstacle is None:
        flagged = None
    else:
        flagged = bool(ir_obstacle)

    dist: Optional[float]
    if isinstance(distance_cm, (int, float)) and distance_cm >= 0:
        dist = float(distance_cm)
    else:
        dist = None

    if flagged is None:
        agreement = "unknown"
        headline = "IR unread"
        advice = "No IR bit in telemetry yet."
    elif flagged and dist is not None and dist <= IR_USEFUL_CM:
        agreement = "agree_near"
        headline = "IR flagged · ultrasonic also close"
        advice = (
            "Both sensors say something is nearby. You still have to STOP — "
            "IR does not cut the motors."
        )
    elif flagged and (dist is None or dist > SONAR_CLOSE_CM):
        agreement = "ir_only"
        headline = "IR flagged · ultrasonic still far"
        advice = (
            "Treat this as a possible false trip until you confirm with your eyes. "
            "Cheap IR modules fire on glossy tables, hands, and room lights. "
            "They are not a measured distance."
        )
    elif not flagged and dist is not None and dist <= SONAR_VERY_CLOSE_CM:
        agreement = "sonar_only"
        headline = "Ultrasonic close · IR still clear"
        advice = (
            "Expected. IR range is short and it often misses dark or matte surfaces. "
            "Use centimetres from HC-SR04 for how far; IR is only a near-field bit."
        )
    elif flagged:
        agreement = "ir_near_band"
        headline = "IR flagged"
        advice = "Something is in the IR module's short beam. Confirm with ultrasonic and your eyes."
    else:
        agreement = "clear"
        headline = "IR clear"
        advice = "Digital OUT is HIGH (no detect). That is not a certified-clear path."

    drive_note = ""
    if driving and flagged:
        drive_note = "Motors are still running. Press STOP. IR is a dashboard flag, not an automatic brake."

    sim_note = ""
    if simulated:
        sim_note = (
            "Simulation trips IR only under ~12 cm so it can disagree with ultrasonic. "
            "On the real rover GPIO19 is independent of the HC-SR04."
        )

    return {
        "flagged": flagged,
        "agreement": agreement,
        "headline": headline,
        "advice": advice,
        "drive_note": drive_note,
        "sim_note": sim_note,
        "stops_motors": False,
        "is_range": False,
        "pin": 19,
        "active_level": "LOW",
    }
