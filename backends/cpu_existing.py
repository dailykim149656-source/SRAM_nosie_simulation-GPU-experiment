"""Existing analytical dataset generation + perceptron inference lane."""

from __future__ import annotations

import time

import numpy as np

from analytical_ground_truth import AnalyticalSRAMModel
from backends.base import BackendCapability, BackendRunOutput
from ml_benchmark import TwoLayerPerceptronRegressor


def capability() -> BackendCapability:
    return BackendCapability(
        name="cpu_existing",
        device="cpu",
        available=True,
        reason="always-available",
        fallback_allowed=False,
        precision="float64",
        backend_kind="cpu",
        runtime_kind="cpu",
        device_display_name="cpu",
    )


def build_numpy_dataset(
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
) -> dict[str, np.ndarray]:
    model = AnalyticalSRAMModel(random_state=seed)
    data = model.generate_dataset(
        n_samples=int(n_samples),
        random_state=int(seed),
        variability_samples=int(variability_samples),
    )
    x = np.column_stack(
        [
            data["temperature"],
            data["voltage"],
            data["cell_ratio"],
            data["width"],
            data["length"],
        ]
    ).astype(float)
    return {
        "X": x,
        "snm": np.asarray(data["snm_mean"], dtype=float),
        "ber": np.asarray(data["ber"], dtype=float),
        "noise_sigma": np.asarray(data["noise_sigma"], dtype=float),
    }


def fit_reference_perceptron(
    *,
    n_samples: int = 4096,
    variability_samples: int = 256,
    seed: int = 42,
    max_iter: int = 4000,
) -> TwoLayerPerceptronRegressor:
    dataset = build_numpy_dataset(
        n_samples=int(n_samples),
        variability_samples=int(variability_samples),
        seed=int(seed),
    )
    model = TwoLayerPerceptronRegressor(
        hidden_dim=24,
        alpha=5e-2,
        learning_rate=0.005,
        max_iter=int(max_iter),
        random_state=int(seed),
    )
    model.fit(dataset["X"], dataset["snm"])
    return model


def predict_on_features(model: TwoLayerPerceptronRegressor, x: np.ndarray) -> np.ndarray:
    return np.asarray(model.predict(np.asarray(x, dtype=float)), dtype=float)


def run_case(
    model: TwoLayerPerceptronRegressor,
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
) -> BackendRunOutput:
    started = time.perf_counter()
    dataset = build_numpy_dataset(
        n_samples=n_samples,
        variability_samples=variability_samples,
        seed=seed,
    )
    predictions = predict_on_features(model, dataset["X"])
    elapsed = time.perf_counter() - started
    return BackendRunOutput(
        device_name="cpu",
        elapsed_sec=float(elapsed),
        predictions=predictions,
        extra={"dataset_shape": tuple(dataset["X"].shape)},
        backend_kind="cpu",
        runtime_kind="cpu",
        device_display_name="cpu",
    )
