"""Environment metadata capture for benchmark runs."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from backends.registry import get_backend_capabilities
from backends.torch_portable import torch, torch_cuda_info


def collect_env_metadata(*, device_mode: str) -> dict[str, object]:
    cuda_available, cuda_detail = torch_cuda_info()
    torch_version = None
    if torch is not None:
        torch_version = str(getattr(torch, "__version__", "unknown"))

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "executable_name": "python",
        "argv0": Path(sys.argv[0]).name if sys.argv else "python",
        "torch_version": torch_version,
        "cuda_available": bool(cuda_available),
        "cuda_device_name": cuda_detail,
        "backend_capabilities": [
            {
                "name": cap.name,
                "device": cap.device,
                "available": cap.available,
                "reason": cap.reason,
                "fallback_allowed": cap.fallback_allowed,
                "precision": cap.precision,
            }
            for cap in get_backend_capabilities(device_mode=device_mode)
        ],
    }
