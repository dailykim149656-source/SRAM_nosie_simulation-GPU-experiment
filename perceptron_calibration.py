"""Utilities for loading/applying calibrated perceptron noise weights.

Expected calibration JSON schema (minimum):
{
  "noise_floor": 0.05,
  "temperature_normalization": {"mean": 310.0, "std": 30.0},
  "voltage_normalization": {"mean": 1.0, "std": 0.15},
  "weights": {
    "W1": [[...], [...]],
    "b1": [...],
    "W2": [[...], [...]],
    "b2": [...]
  }
}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

import numpy as np


ENV_CALIBRATION_PATH = "SRAM_PERCEPTRON_CALIBRATION"
DEFAULT_CALIBRATION_PATH = (
    Path(__file__).resolve().parent
    / "spice_validation"
    / "calibration"
    / "perceptron_noise_weights.json"
)


def resolve_calibration_path(path: Optional[str] = None) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    env_path = os.environ.get(ENV_CALIBRATION_PATH, "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    return DEFAULT_CALIBRATION_PATH


def load_perceptron_calibration(path: Optional[str] = None) -> Optional[dict[str, Any]]:
    calibration_path = resolve_calibration_path(path)
    if not calibration_path.exists():
        return None
    try:
        raw = json.loads(calibration_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _to_array(value: Any) -> Optional[np.ndarray]:
    try:
        arr = np.asarray(value, dtype=float)
    except Exception:
        return None
    if arr.size == 0:
        return None
    return arr


def apply_perceptron_calibration(model: Any, calibration: Mapping[str, Any]) -> bool:
    weights = calibration.get("weights", calibration)
    if not isinstance(weights, Mapping):
        return False

    w1 = _to_array(weights.get("W1"))
    b1 = _to_array(weights.get("b1"))
    w2 = _to_array(weights.get("W2"))
    b2 = _to_array(weights.get("b2"))
    if w1 is None or b1 is None or w2 is None or b2 is None:
        return False

    if not all(hasattr(model, name) for name in ("W1", "b1", "W2", "b2")):
        return False

    if w1.shape != np.asarray(model.W1).shape:
        return False
    if b1.shape != np.asarray(model.b1).shape:
        return False
    if w2.shape != np.asarray(model.W2).shape:
        return False
    if b2.shape != np.asarray(model.b2).shape:
        return False

    model.W1 = w1.copy()
    model.b1 = b1.copy()
    model.W2 = w2.copy()
    model.b2 = b2.copy()

    tnorm = calibration.get("temperature_normalization", {})
    if isinstance(tnorm, Mapping):
        t_mean = tnorm.get("mean")
        t_std = tnorm.get("std")
        if t_mean is not None:
            model.temp_mean = float(t_mean)
        if t_std is not None and float(t_std) > 0:
            model.temp_std = float(t_std)

    vnorm = calibration.get("voltage_normalization", {})
    if isinstance(vnorm, Mapping):
        v_mean = vnorm.get("mean")
        v_std = vnorm.get("std")
        if v_mean is not None:
            model.volt_mean = float(v_mean)
        if v_std is not None and float(v_std) > 0:
            model.volt_std = float(v_std)

    return True


def load_and_apply_perceptron_calibration(model: Any, path: Optional[str] = None) -> bool:
    calibration = load_perceptron_calibration(path=path)
    if calibration is None:
        return False
    return apply_perceptron_calibration(model=model, calibration=calibration)


class PerceptronNoiseBase:
    """공통 2층 MLP 노이즈 모델. PerceptronGateFunction과 PerceptronNoiseModel이 공유."""

    def __init__(
        self,
        input_dim: int = 2,
        hidden_dim: int = 16,
        use_calibration: bool = True,
        calibration_path: Optional[str] = None,
    ) -> None:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(1.0 / input_dim)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, 1) * np.sqrt(1.0 / hidden_dim)
        self.b2 = np.zeros(1)

        self.temp_mean = 310.0
        self.temp_std = 30.0
        self.volt_mean = 1.0
        self.volt_std = 0.15
        self.calibration_loaded = False

        if use_calibration:
            self.calibration_loaded = load_and_apply_perceptron_calibration(
                self, path=calibration_path
            )

    def normalize_inputs(self, temperature: float, voltage: float) -> np.ndarray:
        norm_temp = (temperature - self.temp_mean) / self.temp_std
        norm_volt = (voltage - self.volt_mean) / self.volt_std
        return np.array([norm_temp, norm_volt])

    def forward(self, temperature: float, voltage: float) -> float:
        x = self.normalize_inputs(temperature, voltage)
        z1 = np.dot(x, self.W1) + self.b1
        a1 = np.maximum(0, z1)
        z2 = np.dot(a1, self.W2) + self.b2
        return float(1.0 / (1.0 + np.exp(-np.clip(z2, -500, 500)))[0])

