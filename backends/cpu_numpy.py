"""Chunked NumPy analytical dataset generation + manual perceptron inference lane."""

from __future__ import annotations

import time

import numpy as np

from analytical_ground_truth import AnalyticalSRAMModel
from backends.base import BackendCapability, BackendRunOutput
from ml_benchmark import TwoLayerPerceptronRegressor


def capability() -> BackendCapability:
    return BackendCapability(
        name="cpu_numpy",
        device="cpu",
        available=True,
        reason="always-available",
        fallback_allowed=False,
        precision="float64",
        backend_kind="cpu",
        runtime_kind="cpu",
        device_display_name="cpu",
    )


def build_chunked_numpy_dataset(
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
    chunk_size: int = 1024,
) -> dict[str, np.ndarray]:
    model = AnalyticalSRAMModel(random_state=seed)
    rng = np.random.default_rng(seed)

    temp = rng.uniform(250.0, 400.0, size=n_samples)
    vdd = rng.uniform(0.6, 1.2, size=n_samples)
    cell_ratio = rng.uniform(1.0, 4.0, size=n_samples)
    width = rng.uniform(0.1, 2.0, size=n_samples)
    length = rng.uniform(0.045, 0.18, size=n_samples)

    sigma_vth = model.pelgrom_sigma_vth(width, length)
    snm_mean = np.empty(n_samples, dtype=float)
    snm_std = np.empty(n_samples, dtype=float)

    chunk = max(int(chunk_size), 1)
    for start in range(0, n_samples, chunk):
        end = min(start + chunk, n_samples)
        sampled_vth = rng.normal(
            loc=model.vth_nom,
            scale=np.maximum(sigma_vth[start:end].reshape(-1, 1, 1), 0.0),
            size=(end - start, int(variability_samples), 6),
        )
        effective_vth = np.mean(sampled_vth, axis=2)
        chunk_snm = model.seevinck_snm(
            vdd[start:end].reshape(-1, 1),
            effective_vth,
            cell_ratio[start:end].reshape(-1, 1),
        )
        snm_mean[start:end] = np.mean(chunk_snm, axis=1)
        snm_std[start:end] = np.std(chunk_snm, axis=1, ddof=1)

    noise_sigma = np.asarray(model.thermal_noise_sigma(temp), dtype=float)
    ber = np.asarray(model.analytical_ber(snm_mean, snm_std, noise_sigma), dtype=float)
    x = np.column_stack([temp, vdd, cell_ratio, width, length]).astype(float)
    return {
        "X": x,
        "snm": snm_mean,
        "ber": ber,
        "noise_sigma": noise_sigma,
    }


def perceptron_predict_numpy(model: TwoLayerPerceptronRegressor, x: np.ndarray) -> np.ndarray:
    x_arr = np.asarray(x, dtype=float)
    x_norm = (x_arr - model.x_mean_) / model.x_std_
    hidden = np.tanh(x_norm @ model.W1_ + model.b1_)
    y_norm = hidden @ model.W2_ + model.b2_
    return np.asarray(y_norm, dtype=float).reshape(-1) * model.y_std_ + model.y_mean_


def run_case(
    model: TwoLayerPerceptronRegressor,
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
) -> BackendRunOutput:
    started = time.perf_counter()
    dataset = build_chunked_numpy_dataset(
        n_samples=n_samples,
        variability_samples=variability_samples,
        seed=seed,
    )
    predictions = perceptron_predict_numpy(model, dataset["X"])
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
