"""Registry for analytical benchmark lanes."""

from __future__ import annotations

from typing import Any

from backends import accelerator_lane, cpu_existing, cpu_numpy
from backends.base import BackendCapability
from backends.torch_portable import get_torch_runtime_metadata


LANE_ORDER = ("cpu_existing", "cpu_numpy", "torch_accelerated")
RUNTIME_GPU_FUNCTIONS = {
    "simulate": "simulate_array_gpu",
    "lifetime": "predict_lifetime_gpu",
    "optimize": "optimize_design_gpu",
}
RUNTIME_CPU_FUNCTIONS = {
    "simulate": "simulate_array",
    "lifetime": "predict_lifetime",
    "optimize": "optimize_design",
}


def get_backend_capabilities(device_mode: str = "auto") -> list[BackendCapability]:
    return [
        cpu_existing.capability(),
        cpu_numpy.capability(),
        accelerator_lane.capability(device_mode=device_mode),
    ]


def get_accelerator_backend_capability(device_mode: str = "auto") -> BackendCapability:
    return accelerator_lane.capability(device_mode=device_mode)


def get_gpu_backend_capability(device_mode: str = "auto") -> BackendCapability:
    return get_accelerator_backend_capability(device_mode=device_mode)


def get_runtime_backend_capabilities(
    problem_kind: str,
    *,
    native_module: Any | None = None,
) -> list[BackendCapability]:
    gpu_function = RUNTIME_GPU_FUNCTIONS.get(problem_kind, "")
    cpu_function = RUNTIME_CPU_FUNCTIONS.get(problem_kind, "")
    runtime = get_torch_runtime_metadata()
    accelerator_available = runtime.accelerator_available
    accelerator_kind = runtime.backend_kind if runtime.accelerator_available else "cpu"
    accelerator_detail = runtime.device_display_name if runtime.accelerator_available else runtime.reason
    runtime_kind = runtime.runtime_kind

    native_gpu_available = bool(
        accelerator_available and native_module is not None and gpu_function and hasattr(native_module, gpu_function)
    )
    native_cpu_available = bool(native_module is not None and cpu_function and hasattr(native_module, cpu_function))

    return [
        BackendCapability(
            name=f"{problem_kind}_native_gpu",
            device=accelerator_kind if accelerator_available else "cuda",
            available=native_gpu_available,
            reason=(
                "native-gpu-available"
                if native_gpu_available
                else accelerator_detail if not accelerator_available else "native-gpu-hook-missing"
            ),
            fallback_allowed=True,
            precision="float64",
            backend_kind=accelerator_kind if accelerator_available else "unknown",
            runtime_kind=runtime_kind if accelerator_available else "unavailable",
            device_display_name=runtime.device_display_name if accelerator_available else accelerator_detail,
        ),
        BackendCapability(
            name=f"{problem_kind}_torch_accelerated",
            device=accelerator_kind if accelerator_available else "cuda",
            available=accelerator_available,
            reason="torch-accelerator-available" if accelerator_available else accelerator_detail,
            fallback_allowed=True,
            precision="float64",
            backend_kind=accelerator_kind if accelerator_available else "unknown",
            runtime_kind=runtime_kind if accelerator_available else "unavailable",
            device_display_name=runtime.device_display_name if accelerator_available else accelerator_detail,
        ),
        BackendCapability(
            name=f"{problem_kind}_native_cpu",
            device="cpu",
            available=native_cpu_available,
            reason="native-cpu-available" if native_cpu_available else "native-cpu-hook-missing",
            fallback_allowed=True,
            precision="mixed",
            backend_kind="cpu",
            runtime_kind="cpu",
            device_display_name="cpu",
        ),
        BackendCapability(
            name=f"{problem_kind}_python_fallback",
            device="cpu",
            available=True,
            reason="always-available",
            fallback_allowed=False,
            precision="mixed",
            backend_kind="cpu",
            runtime_kind="cpu",
            device_display_name="cpu",
        ),
    ]
