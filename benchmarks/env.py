"""Environment metadata capture for benchmark runs."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from backends.registry import get_backend_capabilities
from backends.torch_portable import get_torch_runtime_metadata


def collect_env_metadata(*, device_mode: str) -> dict[str, object]:
    runtime = get_torch_runtime_metadata()

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "executable_name": "python",
        "argv0": Path(sys.argv[0]).name if sys.argv else "python",
        "torch_version": runtime.torch_version,
        "torch_build_tag": runtime.torch_build_tag,
        "accelerator_available": bool(runtime.accelerator_available),
        "accelerator_backend_kind": runtime.backend_kind,
        "accelerator_runtime_kind": runtime.runtime_kind,
        "accelerator_device_display_name": runtime.device_display_name,
        "cuda_version": runtime.cuda_version,
        "hip_version": runtime.hip_version,
        "cuda_available": bool(runtime.accelerator_available and runtime.backend_kind == "cuda"),
        "cuda_device_name": runtime.device_display_name if runtime.backend_kind == "cuda" else "cuda-unavailable",
        "backend_capabilities": [
            {
                "name": cap.name,
                "device": cap.device,
                "available": cap.available,
                "reason": cap.reason,
                "fallback_allowed": cap.fallback_allowed,
                "precision": cap.precision,
                "backend_kind": cap.backend_kind,
                "runtime_kind": cap.runtime_kind,
                "device_display_name": cap.device_display_name,
            }
            for cap in get_backend_capabilities(device_mode=device_mode)
        ],
    }
