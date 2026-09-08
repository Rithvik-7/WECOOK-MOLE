from __future__ import annotations

from typing import Optional


def relative_mm(adc_raw: Optional[int], adc0: Optional[float], adc1: Optional[float],
                mm0: Optional[float], mm1: Optional[float]) -> Optional[float]:
    if adc_raw is None or None in (adc0, adc1, mm0, mm1):
        return None
    span = adc1 - adc0
    if abs(span) < 1e-6:
        return None
    return mm0 + (adc_raw - adc0) * (mm1 - mm0) / span


def tilt_change(roll: Optional[float], pitch: Optional[float],
                roll0: Optional[float], pitch0: Optional[float]) -> Optional[float]:
    if None in (roll, pitch, roll0, pitch0):
        return None
    dr = roll - roll0
    dp = pitch - pitch0
    return (dr * dr + dp * dp) ** 0.5
