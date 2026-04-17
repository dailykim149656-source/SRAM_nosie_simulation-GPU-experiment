"""Benchmark timing and fidelity metrics."""

from __future__ import annotations

import math
from statistics import fmean, median, pstdev

import numpy as np


def summarize_elapsed(elapsed_values: list[float], n_samples: int) -> dict[str, float]:
    values = [float(v) for v in elapsed_values if float(v) >= 0.0]
    if not values:
        return {
            "wall_clock_sec": 0.0,
            "wall_clock_sec_mean": 0.0,
            "wall_clock_sec_std": 0.0,
            "wall_clock_sec_p95": 0.0,
            "throughput_samples_per_sec": 0.0,
        }

    values_sorted = sorted(values)
    p95_index = min(max(int(math.ceil(len(values_sorted) * 0.95)) - 1, 0), len(values_sorted) - 1)
    wall_clock = float(median(values_sorted))
    return {
        "wall_clock_sec": wall_clock,
        "wall_clock_sec_mean": float(fmean(values_sorted)),
        "wall_clock_sec_std": float(pstdev(values_sorted)) if len(values_sorted) > 1 else 0.0,
        "wall_clock_sec_p95": float(values_sorted[p95_index]),
        "throughput_samples_per_sec": (float(n_samples) / wall_clock) if wall_clock > 0.0 else 0.0,
    }


def summarize_predictions(predictions: np.ndarray) -> dict[str, float]:
    arr = np.asarray(predictions, dtype=float).reshape(-1)
    if arr.size == 0:
        return {"mean_prediction": 0.0, "std_prediction": 0.0}
    return {
        "mean_prediction": float(np.mean(arr)),
        "std_prediction": float(np.std(arr)),
    }


def compare_predictions(left: np.ndarray, right: np.ndarray) -> dict[str, float]:
    left_arr = np.asarray(left, dtype=float).reshape(-1)
    right_arr = np.asarray(right, dtype=float).reshape(-1)
    if left_arr.shape != right_arr.shape:
        raise ValueError("prediction shape mismatch")
    delta = np.abs(left_arr - right_arr)
    return {
        "max_abs_delta": float(np.max(delta)) if delta.size else 0.0,
        "mean_abs_delta": float(np.mean(delta)) if delta.size else 0.0,
        "rmse": float(np.sqrt(np.mean((left_arr - right_arr) ** 2))) if delta.size else 0.0,
    }
