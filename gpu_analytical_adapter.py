"""Compatibility facade for analytical benchmark helpers."""

from __future__ import annotations

from backends.cpu_existing import build_numpy_dataset, fit_reference_perceptron
from backends.cpu_numpy import build_chunked_numpy_dataset, perceptron_predict_numpy
from backends.torch_portable import (
    TorchExportedPerceptron,
    build_torch_dataset,
    export_perceptron_to_torch,
    perceptron_predict_torch,
    torch,
    torch_cuda_info,
)

__all__ = [
    "TorchExportedPerceptron",
    "build_numpy_dataset",
    "build_chunked_numpy_dataset",
    "build_torch_dataset",
    "export_perceptron_to_torch",
    "fit_reference_perceptron",
    "perceptron_predict_numpy",
    "perceptron_predict_torch",
    "torch",
    "torch_cuda_info",
]
