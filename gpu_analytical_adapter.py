"""Compatibility facade for analytical benchmark helpers."""

from __future__ import annotations

from backends.cpu_existing import build_numpy_dataset, fit_reference_perceptron
from backends.cpu_numpy import build_chunked_numpy_dataset, perceptron_predict_numpy
from backends.torch_portable import (
    TorchExportedPerceptron,
    TorchRuntimeInfo,
    build_torch_dataset,
    export_perceptron_to_torch,
    get_torch_runtime_metadata,
    perceptron_predict_torch,
    resolve_torch_runtime,
    torch,
    torch_cuda_info,
)

__all__ = [
    "TorchExportedPerceptron",
    "TorchRuntimeInfo",
    "build_numpy_dataset",
    "build_chunked_numpy_dataset",
    "build_torch_dataset",
    "export_perceptron_to_torch",
    "fit_reference_perceptron",
    "get_torch_runtime_metadata",
    "perceptron_predict_numpy",
    "perceptron_predict_torch",
    "resolve_torch_runtime",
    "torch",
    "torch_cuda_info",
]
