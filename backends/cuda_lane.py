"""CUDA-specific wrapper for the analytical benchmark torch lane."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from backends.base import BackendCapability, BackendRunOutput
from backends.torch_portable import (
    TorchExportedPerceptron,
    build_torch_dataset,
    export_perceptron_to_torch,
    perceptron_predict_torch,
    torch,
    torch_cuda_info,
)


def capability(device_mode: str = "auto") -> BackendCapability:
    requested = str(device_mode).strip().lower() or "auto"
    force_cpu = os.environ.get("SRAM_FORCE_CPU", "").strip().lower() in {"1", "true", "yes"}
    if force_cpu:
        return BackendCapability(
            name="gpu_pytorch",
            device="cuda",
            available=False,
            reason="forced_cpu_env",
            fallback_allowed=True,
            precision="float32",
        )
    if requested == "cpu":
        return BackendCapability(
            name="gpu_pytorch",
            device="cuda",
            available=False,
            reason="device_mode_cpu",
            fallback_allowed=True,
            precision="float32",
        )

    available, detail = torch_cuda_info()
    return BackendCapability(
        name="gpu_pytorch",
        device="cuda",
        available=bool(available),
        reason="cuda-ready" if available else detail,
        fallback_allowed=True,
        precision="float32",
    )


def export_model(model: Any) -> TorchExportedPerceptron:
    return export_perceptron_to_torch(model, device="cuda")


def predict_on_features(exported_model: TorchExportedPerceptron, x: np.ndarray) -> np.ndarray:
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")
    x_tensor = torch.tensor(np.asarray(x, dtype=np.float32), dtype=torch.float32, device=exported_model.device)
    predictions = perceptron_predict_torch(exported_model, x_tensor)
    if exported_model.device == "cuda":
        torch.cuda.synchronize()
    return predictions.detach().cpu().numpy()


def run_case(
    exported_model: TorchExportedPerceptron,
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
) -> BackendRunOutput:
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")

    import time

    started = time.perf_counter()
    dataset = build_torch_dataset(
        n_samples=n_samples,
        variability_samples=variability_samples,
        seed=seed,
        device=exported_model.device,
    )
    predictions = perceptron_predict_torch(exported_model, dataset["X"])
    if exported_model.device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    available, detail = torch_cuda_info()
    device_name = detail if available else exported_model.device
    return BackendRunOutput(
        device_name=device_name,
        elapsed_sec=float(elapsed),
        predictions=predictions.detach().cpu().numpy(),
        extra={"dataset_shape": tuple(dataset["X"].shape)},
    )
