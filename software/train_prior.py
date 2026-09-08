"""Train shipped tabletop-prior anomaly models. Run from software/: python train_prior.py"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
N = 240
CONTAMINATION = 0.05


def _ensemble(X: np.ndarray, seed: int):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    forest = IsolationForest(
        n_estimators=120,
        contamination=CONTAMINATION,
        random_state=seed,
    )
    forest.fit(Xs)
    lof = LocalOutlierFactor(
        n_neighbors=20,
        contamination=CONTAMINATION,
        novelty=True,
    )
    lof.fit(Xs)
    return scaler, forest, lof


def quiet_node_a(rng: np.random.Generator) -> np.ndarray:
    tilt = np.clip(rng.normal(0.18, 0.12, N), 0.0, 1.1)
    vib = np.clip(rng.normal(0.0045, 0.0015, N), 0.001, 0.012)
    d_tilt = rng.normal(0.0, 0.04, N)
    gap = np.clip(rng.normal(0.15, 0.25, N), 0.0, 1.2)
    return np.column_stack([tilt, vib, d_tilt, gap])


def quiet_node_b(rng: np.random.Generator) -> np.ndarray:
    tilt = np.clip(rng.normal(0.14, 0.10, N), 0.0, 1.0)
    vib = np.clip(rng.normal(0.0038, 0.0012, N), 0.001, 0.010)
    d_tilt = rng.normal(0.0, 0.035, N)
    return np.column_stack([tilt, vib, d_tilt])


def quiet_joint(rng: np.random.Generator) -> np.ndarray:
    tilt_res = np.clip(np.abs(rng.normal(0.05, 0.08, N)), 0.0, 0.6)
    vib_res = np.clip(np.abs(rng.normal(0.0008, 0.0006, N)), 0.0, 0.004)
    return np.column_stack([tilt_res, vib_res])


def dump_node(node_id: int, X: np.ndarray, names: list[str], seed: int) -> Path:
    scaler, forest, lof = _ensemble(X, seed)
    path = ARTIFACTS / f"node{node_id}.prior.joblib"
    joblib.dump(
        {
            "scaler": scaler,
            "forest": forest,
            "lof": lof,
            "names": names,
            "n_train": int(X.shape[0]),
            "trained_at": "tabletop-prior",
            "prior": True,
        },
        path,
    )
    return path


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    a = dump_node(
        1,
        quiet_node_a(rng),
        ["tilt_change_deg", "vibration_g", "d_tilt", "relative_mm"],
        1,
    )
    b = dump_node(
        2,
        quiet_node_b(rng),
        ["tilt_change_deg", "vibration_g", "d_tilt"],
        2,
    )
    Xj = quiet_joint(rng)
    scaler, forest, _lof = _ensemble(Xj, 3)
    joint = ARTIFACTS / "joint.prior.joblib"
    joblib.dump(
        {
            "scaler": scaler,
            "forest": forest,
            "n_train": int(Xj.shape[0]),
            "trained_at": "tabletop-prior",
            "prior": True,
            "names": ["abs_tilt_residual_deg", "abs_vib_residual_g"],
        },
        joint,
    )
    print(f"Wrote {a}")
    print(f"Wrote {b}")
    print(f"Wrote {joint}")


if __name__ == "__main__":
    main()
