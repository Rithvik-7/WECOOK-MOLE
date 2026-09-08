from __future__ import annotations

from typing import Optional

import numpy as np


def node_vector(tilt_change: Optional[float], vibration: Optional[float],
                d_tilt: Optional[float], relative_mm: Optional[float], *,
                node_id: int, include_mm: bool) -> Optional[list[float]]:
    if tilt_change is None or vibration is None or d_tilt is None:
        return None
    row = [float(tilt_change), float(vibration), float(d_tilt)]
    if node_id == 1 and include_mm:
        if relative_mm is None:
            return None
        row.append(float(relative_mm))
    return row


def feature_names(node_id: int, include_mm: bool) -> list[str]:
    names = ["tilt_change_deg", "vibration_g", "d_tilt"]
    if node_id == 1 and include_mm:
        names.append("relative_mm")
    return names


def joint_vector(a_tilt: Optional[float], b_tilt: Optional[float],
                 a_vib: Optional[float], b_vib: Optional[float]) -> Optional[list[float]]:
    if None in (a_tilt, b_tilt, a_vib, b_vib):
        return None
    return [abs(a_tilt - b_tilt), abs(a_vib - b_vib)]


def as_array(rows: list[list[float]]) -> np.ndarray:
    return np.asarray(rows, dtype=float)
