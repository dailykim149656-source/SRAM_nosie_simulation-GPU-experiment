"""Compatibility shim for the canonical accelerator-neutral torch lane."""

from backends.accelerator_lane import capability, export_model, predict_on_features, run_case
from backends.torch_portable import TorchExportedPerceptron

__all__ = [
    "TorchExportedPerceptron",
    "capability",
    "export_model",
    "predict_on_features",
    "run_case",
]
