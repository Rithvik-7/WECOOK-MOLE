from __future__ import annotations

from collections import deque
from typing import Optional, Sequence
import warnings

import numpy as np
from sklearn.linear_model import HuberRegressor, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error

HORIZON = 30
WINDOW = 60
LAGS = 6
MIN_POINTS = 18
FORECAST_LABEL = "30 s sensor trend forecast — not a collapse prediction."


class SeriesForecast:
    """Holdout-selected autoregressive forecast for a 1 Hz signal."""

    def __init__(
        self,
        metric: str = "signal",
        unit: str = "",
        watch_threshold: Optional[float] = None,
        alert_threshold: Optional[float] = None,
    ) -> None:
        self.metric = metric
        self.unit = unit
        self.watch_threshold = watch_threshold
        self.alert_threshold = alert_threshold
        self.values: deque[float] = deque(maxlen=300)
        self.timestamps: deque[float] = deque(maxlen=300)
        self._cache = None
        self._cache_key = None

    def push(self, value: Optional[float], timestamp: Optional[float] = None) -> None:
        if value is None:
            return
        self.values.append(float(value))
        if timestamp is None:
            timestamp = (self.timestamps[-1] + 1.0) if self.timestamps else 0.0
        self.timestamps.append(float(timestamp))
        self._cache = None
        self._cache_key = None

    @staticmethod
    def _supervised(values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
        rows, targets = [], []
        for i in range(LAGS, len(values)):
            window = list(values[i - LAGS : i])
            rows.append(window + [float(np.mean(window)), float(window[-1] - window[0])])
            targets.append(values[i])
        return np.asarray(rows, dtype=float), np.asarray(targets, dtype=float)

    @staticmethod
    def _features(window: Sequence[float]) -> np.ndarray:
        w = list(window[-LAGS:])
        return np.asarray(
            w + [float(np.mean(w)), float(w[-1] - w[0])], dtype=float
        ).reshape(1, -1)

    def _empty(self, state: str, reason: str) -> dict:
        return {
            "state": state,
            "metric": self.metric,
            "unit": self.unit,
            "model": "sklearn holdout-selected autoregression",
            "selected": None,
            "candidates": {},
            "points": [],
            "lower": [],
            "upper": [],
            "mae": None,
            "quality": "INSUFFICIENT_DATA",
            "samples": len(self.values),
            "slope_per_s": None,
            "seconds_to_watch": None,
            "seconds_to_alert": None,
            "surprise_z": None,
            "surprise_state": "INACTIVE",
            "reason": reason,
            "label": FORECAST_LABEL,
        }

    @staticmethod
    def _candidate_models() -> dict:
        return {
            "Ridge": Ridge(alpha=1.0),
            "HuberRegressor": HuberRegressor(max_iter=80),
            "LinearRegression": LinearRegression(),
        }

    def predict(self) -> dict:
        key = (len(self.values), self.values[-1] if self.values else None)
        if self._cache is not None and self._cache_key == key:
            return self._cache
        result = self._predict()
        self._cache = result
        self._cache_key = key
        return result

    def _predict(self) -> dict:
        y = list(self.values)[-WINDOW:]
        if len(y) < MIN_POINTS:
            return self._empty(
                "LEARNING",
                f"Need {MIN_POINTS} valid 1 Hz points; have {len(y)}.",
            )

        X, target = self._supervised(y)
        if len(target) < 8:
            return self._empty("LEARNING", "Not enough lag windows yet.")

        split = max(5, int(len(target) * 0.75))
        split = min(split, len(target) - 2)
        X_train, y_train = X[:split], target[:split]
        X_val, y_val = X[split:], target[split:]
        scores: dict[str, float] = {}
        if len(y_val) >= 2:
            persist = float(mean_absolute_error(y_val, np.asarray(target[split - 1 : -1], dtype=float)))
            scores["persistence"] = persist
            for name, estimator in self._candidate_models().items():
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        estimator.fit(X_train, y_train)
                    pred = estimator.predict(X_val)
                    scores[name] = float(mean_absolute_error(y_val, pred))
                except Exception:
                    continue
        selected = min(scores, key=scores.get) if scores else "Ridge"
        validation_mae = scores.get(selected)

        if selected == "persistence":
            model = Ridge(alpha=1.0)
            model.fit(X, target)
            selected_label = "Ridge fallback (persistence won holdout; used for rollout)"
        elif selected in self._candidate_models():
            model = self._candidate_models()[selected]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(X, target)
            selected_label = f"sklearn {selected} (holdout-selected)"
        else:
            model = Ridge(alpha=1.0)
            model.fit(X, target)
            selected_label = "sklearn Ridge autoregression"

        rolling = list(y[-LAGS:])
        pred_path: list[float] = []
        for _ in range(HORIZON):
            value = float(model.predict(self._features(rolling))[0])
            value = max(0.0, value)
            pred_path.append(value)
            rolling.append(value)
            rolling = rolling[-LAGS:]

        residual_std = 0.0
        if validation_mae is not None and len(y_val) >= 2 and selected != "persistence":
            fitted = self._candidate_models().get(selected, Ridge(alpha=1.0))
            try:
                fitted.fit(X_train, y_train)
                residual_std = float(np.std(y_val - fitted.predict(X_val)))
            except Exception:
                residual_std = float(validation_mae)

        trend_x = np.arange(min(15, len(y)), dtype=float).reshape(-1, 1)
        trend_y = np.asarray(y[-len(trend_x) :], dtype=float)
        trend = Ridge(alpha=1.0).fit(trend_x, trend_y)
        slope = float(trend.coef_[0])
        current = float(y[-1])

        def eta(threshold: Optional[float]) -> Optional[float]:
            if threshold is None or slope <= 0.002:
                return None
            gap = threshold - current
            if gap <= 0:
                return 0.0
            seconds = gap / slope
            return round(float(seconds), 1) if seconds <= 300 else None

        if validation_mae is None:
            quality = "PENDING"
        else:
            scale = max(float(np.ptp(y)), abs(float(np.mean(y))) * 0.1, 1e-6)
            ratio = validation_mae / scale
            quality = "GOOD" if ratio <= 0.15 else "FAIR" if ratio <= 0.35 else "LOW"

        surprise_z = None
        surprise_state = "INACTIVE"
        if len(y) > LAGS:
            one_step = float(model.predict(self._features(y[-LAGS - 1 : -1]))[0])
            scale = max(float(np.ptp(y)), abs(current), 1e-3)
            denom = max(validation_mae or 0.0, residual_std, scale * 0.05)
            surprise_z = abs(current - one_step) / denom
            surprise_state = "UNUSUAL" if surprise_z >= 3.0 else "READY"

        band = max(residual_std, validation_mae or 0.0)
        rounded_scores = {key: round(val, 5) for key, val in scores.items()}
        return {
            "state": "READY",
            "metric": self.metric,
            "unit": self.unit,
            "model": selected_label,
            "selected": selected if selected != "persistence" else "Ridge",
            "candidates": rounded_scores,
            "points": [round(v, 5) for v in pred_path],
            "lower": [round(max(0.0, v - band), 5) for v in pred_path],
            "upper": [round(v + band, 5) for v in pred_path],
            "mae": None if validation_mae is None else round(validation_mae, 5),
            "quality": quality,
            "samples": len(y),
            "slope_per_s": round(slope, 5),
            "seconds_to_watch": eta(self.watch_threshold),
            "seconds_to_alert": eta(self.alert_threshold),
            "surprise_z": None if surprise_z is None else round(float(surprise_z), 3),
            "surprise_state": surprise_state,
            "reason": (
                f"{selected_label} uses {len(y)} recent points; "
                f"holdout MAE {validation_mae:.4g} {self.unit}."
                if validation_mae is not None
                else f"{selected_label} uses {len(y)} recent points."
            ),
            "label": FORECAST_LABEL,
        }
