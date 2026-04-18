"""Canonical accelerator-neutral wrapper for the analytical benchmark torch lane."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from backends.base import BackendCapability, BackendRunOutput
from backends.torch_portable import (
    TorchExportedPerceptron,
    build_torch_dataset,
    export_perceptron_to_torch,
    get_torch_runtime_metadata,
    perceptron_predict_torch,
    synchronize_torch_device,
    torch,
)


LANE_NAME = "torch_accelerated"


def _capability_from_runtime(
    *,
    available: bool,
    reason: str,
    runtime_kind: str,
    backend_kind: str,
    device_display_name: str,
) -> BackendCapability:
    return BackendCapability(
        name=LANE_NAME,
        device="cuda" if available else "cpu",
        available=bool(available),
        reason=str(reason),
        fallback_allowed=True,
        precision="float32",
        backend_kind=str(backend_kind),
        runtime_kind=str(runtime_kind),
        device_display_name=str(device_display_name),
    )


def capability(device_mode: str = "auto") -> BackendCapability:
    requested = str(device_mode).strip().lower() or "auto"
    runtime = get_torch_runtime_metadata()
    force_cpu = os.environ.get("SRAM_FORCE_CPU", "").strip().lower() in {"1", "true", "yes"}
    if force_cpu:
        return _capability_from_runtime(
            available=False,
            reason="forced_cpu_env",
            runtime_kind=runtime.runtime_kind,
            backend_kind=runtime.backend_kind,
            device_display_name=runtime.device_display_name,
        )
    if requested == "cpu":
        return _capability_from_runtime(
            available=False,
            reason="device_mode_cpu",
            runtime_kind=runtime.runtime_kind,
            backend_kind=runtime.backend_kind,
            device_display_name=runtime.device_display_name,
        )

    return _capability_from_runtime(
        available=runtime.accelerator_available,
        reason=runtime.reason,
        runtime_kind=runtime.runtime_kind,
        backend_kind=runtime.backend_kind,
        device_display_name=runtime.device_display_name,
    )


def export_model(model: Any) -> TorchExportedPerceptron:
    return export_perceptron_to_torch(model, device="gpu")


def predict_on_features(exported_model: TorchExportedPerceptron, x: np.ndarray) -> np.ndarray:
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")
    x_tensor = torch.tensor(np.asarray(x, dtype=np.float32), dtype=torch.float32, device=exported_model.device)
    predictions = perceptron_predict_torch(exported_model, x_tensor)
    synchronize_torch_device(exported_model.device, exported_model.backend_kind)
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
    synchronize_torch_device(exported_model.device, exported_model.backend_kind)
    elapsed = time.perf_counter() - started
    return BackendRunOutput(
        device_name=exported_model.device_display_name,
        elapsed_sec=float(elapsed),
        predictions=predictions.detach().cpu().numpy(),
        extra={"dataset_shape": tuple(dataset["X"].shape)},
        backend_kind=exported_model.backend_kind,
        runtime_kind=exported_model.runtime_kind,
        device_display_name=exported_model.device_display_name,
    )
