from __future__ import annotations

from typing import Optional


def compare_ab(a_tilt: Optional[float], b_tilt: Optional[float]) -> str:
    if a_tilt is None or b_tilt is None:
        return "Not enough paired tilt to compare Node A with Node B."
    if a_tilt >= 3.0 and b_tilt < 1.0:
        return (
            f"Node A tilt change {a_tilt:.2f}° while Node B is {b_tilt:.2f}°. "
            "Looks local to Node A, not whole-table motion."
        )
    if a_tilt >= 3.0 and b_tilt >= 3.0 and abs(a_tilt - b_tilt) < 2.0:
        return (
            f"Node A {a_tilt:.2f}° and Node B {b_tilt:.2f}° moved together. "
            "Could be table/model or common vibration — not proof of a collapse."
        )
    return f"Node A tilt change {a_tilt:.2f}°, Node B {b_tilt:.2f}°."


def compose(*, rule_a: str, rule_b: str, ai_a: str, ai_b: str, ab: str,
            forecast_note: str) -> str:
    return " ".join([rule_a, ab, ai_a, forecast_note, rule_b, ai_b])
