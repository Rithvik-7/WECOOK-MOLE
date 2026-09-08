from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

MIN_TRAIN = 120
SIM_MIN_TRAIN = 36
CONTAMINATION = 0.05


@dataclass
class AnomalyResult:
    state: str  # INACTIVE | READY | UNUSUAL
    score: Optional[float]
    top_feature: Optional[str]
    n_train: int
    trained_at: Optional[str]
    feature_names: list[str]
    reason: str
    isolation_state: str = "INACTIVE"
    lof_state: str = "INACTIVE"
    votes: int = 0
    simulated: bool = False
    prior: bool = False
    models: list[str] = field(default_factory=lambda: [
        "sklearn IsolationForest",
        "sklearn LocalOutlierFactor",
    ])
    min_train: int = MIN_TRAIN


class NodeAnomaly:
    """Per-node ensemble: Isolation Forest (primary) + Local Outlier Factor."""

    def __init__(self, node_id: int, artifact_dir: Path, *, load_existing: bool = True):
        self.node_id = node_id
        self.path = artifact_dir / f"node{node_id}.joblib"
        self.prior_path = artifact_dir / f"node{node_id}.prior.joblib"
        self.scaler: Optional[StandardScaler] = None
        self.forest: Optional[IsolationForest] = None
        self.lof: Optional[LocalOutlierFactor] = None
        self.names: list[str] = []
        self.n_train = 0
        self.trained_at: Optional[str] = None
        self.healthy: list[list[float]] = []
        self.load_error: Optional[str] = None
        self.simulated = False
        self.prior = False
        if load_existing:
            self.load()

    def load(self) -> None:
        for path, is_prior in ((self.path, False), (self.prior_path, True)):
            if not path.exists():
                continue
            try:
                blob = joblib.load(path)
                self.scaler = blob["scaler"]
                self.forest = blob["forest"]
                self.lof = blob.get("lof")
                self.names = list(blob["names"])
                self.n_train = int(blob["n_train"])
                self.trained_at = blob.get("trained_at")
                self.simulated = False
                self.prior = bool(blob.get("prior", is_prior))
                return
            except (KeyError, OSError, ValueError, TypeError, EOFError) as exc:
                self.load_error = f"Could not load saved model: {exc}"
                self.scaler = None
                self.forest = None
                self.lof = None

    def reset(self) -> None:
        self.scaler = None
        self.forest = None
        self.lof = None
        self.names = []
        self.n_train = 0
        self.trained_at = None
        self.simulated = False
        self.prior = False
        self.healthy.clear()
        if self.path.exists():
            self.path.unlink()
        self.load()

    def note_healthy(self, row: list[float], names: list[str]) -> None:
        if self.forest is not None and not self.simulated:
            return
        if self.simulated:
            return
        if self.names and names != self.names:
            self.healthy.clear()
        self.names = names
        self.healthy.append(row)
        if len(self.healthy) > 400:
            self.healthy = self.healthy[-400:]

    def can_train(self, *, live: bool, latched_or_watch: bool) -> tuple[bool, str]:
        if not live:
            return False, "Persisted training is blocked in simulated mode."
        if latched_or_watch:
            return False, "Training is blocked while WATCH/ALERT is active."
        if len(self.healthy) < MIN_TRAIN:
            return False, f"Need {MIN_TRAIN} live NORMAL samples, have {len(self.healthy)}."
        return True, "ok"

    def _fit(self, trained_at: str, *, persist: bool) -> str:
        X = np.asarray(self.healthy, dtype=float)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        forest = IsolationForest(
            n_estimators=100,
            contamination=CONTAMINATION,
            random_state=0,
        )
        forest.fit(Xs)
        neighbors = max(5, min(20, X.shape[0] // 3))
        lof = LocalOutlierFactor(
            n_neighbors=neighbors,
            contamination=CONTAMINATION,
            novelty=True,
        )
        lof.fit(Xs)
        self.scaler = scaler
        self.forest = forest
        self.lof = lof
        self.n_train = int(X.shape[0])
        self.trained_at = trained_at
        self.simulated = not persist
        self.prior = False
        if persist:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(
                {
                    "scaler": scaler,
                    "forest": forest,
                    "lof": lof,
                    "names": self.names,
                    "n_train": self.n_train,
                    "trained_at": trained_at,
                },
                self.path,
            )
            return (
                f"Trained Isolation Forest + LOF on {self.n_train} NORMAL samples "
                f"for node {self.node_id}."
            )
        return (
            f"Simulation-only Isolation Forest + LOF fitted on {self.n_train} samples "
            f"for node {self.node_id}. Not saved."
        )

    def train(self, trained_at: str) -> str:
        return self._fit(trained_at, persist=True)

    def maybe_fit_simulation(self) -> Optional[str]:
        if self.forest is not None or len(self.healthy) < SIM_MIN_TRAIN:
            return None
        if not self.names:
            return None
        return self._fit("simulation-only", persist=False)

    def score_row(self, row: Optional[list[float]], names: list[str]) -> AnomalyResult:
        min_train = SIM_MIN_TRAIN if self.simulated else MIN_TRAIN
        if self.forest is None or self.scaler is None:
            n = len(self.healthy)
            return AnomalyResult(
                state="INACTIVE",
                score=None,
                top_feature=None,
                n_train=n,
                trained_at=None,
                feature_names=names,
                reason=f"Anomaly ensemble INACTIVE. {n}/{min_train} NORMAL samples collected.",
                min_train=min_train,
            )
        if row is None or names != self.names:
            return AnomalyResult(
                state="READY",
                score=None,
                top_feature=None,
                n_train=self.n_train,
                trained_at=self.trained_at,
                feature_names=self.names,
                reason="Features unavailable this sample; ensemble stays READY, no new score.",
                simulated=self.simulated,
                min_train=min_train,
            )
        x = np.asarray(row, dtype=float).reshape(1, -1)
        xs = self.scaler.transform(x)
        decision = float(self.forest.decision_function(xs)[0])
        unusual_score = -decision
        if_pred = int(self.forest.predict(xs)[0])
        lof_pred = 1
        lof_state = "INACTIVE"
        if self.lof is not None:
            lof_pred = int(self.lof.predict(xs)[0])
            lof_state = "UNUSUAL" if lof_pred == -1 else "READY"
        isolation_state = "UNUSUAL" if if_pred == -1 else "READY"
        votes = int(if_pred == -1) + int(lof_pred == -1)
        z = xs.reshape(-1)
        top = self.names[int(np.argmax(np.abs(z)))]
        prefix = "Tabletop prior " if self.prior else ("Simulation-only " if self.simulated else "")
        if if_pred == -1:
            extra = " LOF agrees." if lof_pred == -1 else " LOF still inliers."
            reason = (
                f"{prefix}Isolation Forest UNUSUAL (score {unusual_score:.3f}). "
                f"Largest deviation: {top}.{extra}"
            )
            state = "UNUSUAL"
        else:
            extra = " LOF flags novelty." if lof_pred == -1 else " Both models match trained normal."
            reason = (
                f"{prefix}Isolation Forest READY (score {unusual_score:.3f}).{extra}"
            )
            state = "UNUSUAL" if lof_pred == -1 else "READY"
        return AnomalyResult(
            state=state,
            score=unusual_score,
            top_feature=top,
            n_train=self.n_train,
            trained_at=self.trained_at,
            feature_names=self.names,
            reason=reason,
            isolation_state=isolation_state,
            lof_state=lof_state,
            votes=votes,
            simulated=self.simulated,
            prior=self.prior,
            min_train=min_train,
        )


class JointAnomaly:
    """Isolation Forest on Node A vs Node B residuals — local vs common motion."""

    NAMES = ["abs_tilt_residual_deg", "abs_vib_residual_g"]

    def __init__(self, artifact_dir: Optional[Path] = None) -> None:
        self.prior_path = None if artifact_dir is None else artifact_dir / "joint.prior.joblib"
        self.scaler: Optional[StandardScaler] = None
        self.forest: Optional[IsolationForest] = None
        self.healthy: list[list[float]] = []
        self.n_train = 0
        self.simulated = False
        self.prior = False
        self.load()

    def load(self) -> None:
        if self.prior_path is None or not self.prior_path.exists():
            return
        try:
            blob = joblib.load(self.prior_path)
            self.scaler = blob["scaler"]
            self.forest = blob["forest"]
            self.n_train = int(blob["n_train"])
            self.simulated = False
            self.prior = True
        except (KeyError, OSError, ValueError, TypeError, EOFError):
            self.scaler = None
            self.forest = None

    def reset(self) -> None:
        self.scaler = None
        self.forest = None
        self.healthy.clear()
        self.n_train = 0
        self.simulated = False
        self.prior = False
        self.load()

    def note_healthy(self, row: list[float]) -> None:
        if self.forest is not None:
            return
        self.healthy.append(row)
        if len(self.healthy) > 400:
            self.healthy = self.healthy[-400:]

    def maybe_fit(self, *, simulated: bool) -> None:
        need = SIM_MIN_TRAIN if simulated else MIN_TRAIN
        if self.forest is not None or len(self.healthy) < need:
            return
        X = np.asarray(self.healthy, dtype=float)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        forest = IsolationForest(
            n_estimators=80,
            contamination=CONTAMINATION,
            random_state=1,
        )
        forest.fit(Xs)
        self.scaler = scaler
        self.forest = forest
        self.n_train = int(X.shape[0])
        self.simulated = simulated

    def score(self, row: Optional[list[float]], a_tilt: Optional[float], b_tilt: Optional[float]) -> dict:
        if self.forest is None or self.scaler is None or row is None:
            return {
                "state": "INACTIVE",
                "score": None,
                "pattern": "UNKNOWN",
                "n_train": len(self.healthy),
                "min_train": SIM_MIN_TRAIN if self.simulated else MIN_TRAIN,
                "feature_names": self.NAMES,
                "model": "sklearn IsolationForest on A–B residual",
                "simulated": self.simulated,
                "reason": (
                    f"Joint A vs B model INACTIVE. {len(self.healthy)} paired NORMAL samples."
                ),
            }
        xs = self.scaler.transform(np.asarray(row, dtype=float).reshape(1, -1))
        decision = float(self.forest.decision_function(xs)[0])
        pred = int(self.forest.predict(xs)[0])
        pattern = "COMMON"
        if a_tilt is not None and b_tilt is not None:
            if a_tilt >= 3.0 and b_tilt < 1.0:
                pattern = "LOCAL_A"
            elif b_tilt >= 3.0 and a_tilt < 1.0:
                pattern = "LOCAL_B"
            elif a_tilt >= 3.0 and b_tilt >= 3.0:
                pattern = "COMMON"
            else:
                pattern = "QUIET"
        unusual = pred == -1
        state = "UNUSUAL" if unusual else "READY"
        reason = (
            f"Joint Isolation Forest {'UNUSUAL' if unusual else 'READY'} "
            f"(score {-decision:.3f}). Pattern {pattern}."
        )
        if self.simulated:
            reason = "Simulation-only " + reason
        elif self.prior:
            reason = "Tabletop prior " + reason
        return {
            "state": state,
            "score": round(-decision, 4),
            "pattern": pattern,
            "n_train": self.n_train,
            "min_train": SIM_MIN_TRAIN if self.simulated else MIN_TRAIN,
            "feature_names": self.NAMES,
            "model": "sklearn IsolationForest on A–B residual",
            "simulated": self.simulated,
            "prior": self.prior,
            "reason": reason,
        }
