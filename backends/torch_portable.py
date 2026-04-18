"""Device-neutral PyTorch helpers for analytical benchmark paths."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any

import numpy as np

try:
    import torch
except Exception:  # pragma: no cover - optional dependency
    torch = None  # type: ignore[assignment]


@dataclass
class TorchExportedPerceptron:
    device: str
    backend_kind: str
    runtime_kind: str
    device_display_name: str
    x_mean: Any
    x_std: Any
    y_mean: float
    y_std: float
    w1: Any
    b1: Any
    w2: Any
    b2: float


@dataclass(frozen=True)
class TorchRuntimeInfo:
    accelerator_available: bool
    torch_device: str
    backend_kind: str
    runtime_kind: str
    device_display_name: str
    torch_version: str | None
    torch_build_tag: str | None
    cuda_version: str | None
    hip_version: str | None
    reason: str

    def to_metadata(self) -> dict[str, object]:
        return asdict(self)


def _torch_version_string() -> str | None:
    if torch is None:
        return None
    return str(getattr(torch, "__version__", "unknown"))


def _torch_build_tag(torch_version: str | None) -> str | None:
    if not torch_version:
        return None
    if "+" not in torch_version:
        return None
    return torch_version.split("+", 1)[1] or None


def _cpu_runtime(reason: str) -> TorchRuntimeInfo:
    torch_version = _torch_version_string()
    return TorchRuntimeInfo(
        accelerator_available=False,
        torch_device="cpu",
        backend_kind="cpu",
        runtime_kind="cpu",
        device_display_name="cpu",
        torch_version=torch_version,
        torch_build_tag=_torch_build_tag(torch_version),
        cuda_version=getattr(getattr(torch, "version", None), "cuda", None) if torch is not None else None,
        hip_version=getattr(getattr(torch, "version", None), "hip", None) if torch is not None else None,
        reason=reason,
    )


def get_torch_runtime_metadata() -> TorchRuntimeInfo:
    force_cpu = os.environ.get("SRAM_FORCE_CPU", "").strip().lower() in {"1", "true", "yes"}
    if force_cpu:
        return _cpu_runtime("forced_cpu_env")
    if torch is None:
        return TorchRuntimeInfo(
            accelerator_available=False,
            torch_device="cpu",
            backend_kind="unknown",
            runtime_kind="unavailable",
            device_display_name="torch-unavailable",
            torch_version=None,
            torch_build_tag=None,
            cuda_version=None,
            hip_version=None,
            reason="torch-unavailable",
        )

    torch_version = _torch_version_string()
    hip_version = getattr(getattr(torch, "version", None), "hip", None)
    cuda_version = getattr(getattr(torch, "version", None), "cuda", None)
    if not bool(torch.cuda.is_available()):
        return TorchRuntimeInfo(
            accelerator_available=False,
            torch_device="cpu",
            backend_kind="unknown",
            runtime_kind="unavailable",
            device_display_name="accelerator-unavailable",
            torch_version=torch_version,
            torch_build_tag=_torch_build_tag(torch_version),
            cuda_version=cuda_version,
            hip_version=hip_version,
            reason="accelerator-unavailable",
        )

    backend_kind = "hip" if hip_version else "cuda"
    runtime_kind = "rocm" if hip_version else "cuda"
    return TorchRuntimeInfo(
        accelerator_available=True,
        torch_device="cuda",
        backend_kind=backend_kind,
        runtime_kind=runtime_kind,
        device_display_name=str(torch.cuda.get_device_name(0)),
        torch_version=torch_version,
        torch_build_tag=_torch_build_tag(torch_version),
        cuda_version=cuda_version,
        hip_version=hip_version,
        reason=f"{backend_kind}-ready",
    )


def torch_cuda_info() -> tuple[bool, str]:
    available, _, detail = torch_accelerator_info()
    return available, detail


def torch_accelerator_info() -> tuple[bool, str, str]:
    runtime = get_torch_runtime_metadata()
    if runtime.accelerator_available:
        return True, runtime.backend_kind, runtime.device_display_name
    return False, "cpu", runtime.reason


def resolve_torch_runtime(device: str = "auto") -> TorchRuntimeInfo:
    requested = str(device).strip().lower() or "auto"
    if requested == "cpu":
        return _cpu_runtime("device_mode_cpu")

    runtime = get_torch_runtime_metadata()
    if requested == "auto":
        return runtime if runtime.accelerator_available else _cpu_runtime(runtime.reason)

    if requested in {"gpu", "accelerator", "cuda", "hip"}:
        if runtime.accelerator_available:
            return runtime
        raise RuntimeError(f"Accelerator-capable PyTorch is unavailable ({runtime.reason})")

    return TorchRuntimeInfo(
        accelerator_available=False,
        torch_device=requested,
        backend_kind=requested,
        runtime_kind=requested,
        device_display_name=requested,
        torch_version=_torch_version_string(),
        torch_build_tag=_torch_build_tag(_torch_version_string()),
        cuda_version=getattr(getattr(torch, "version", None), "cuda", None) if torch is not None else None,
        hip_version=getattr(getattr(torch, "version", None), "hip", None) if torch is not None else None,
        reason="explicit-device",
    )


def resolve_torch_accelerator(device: str = "auto") -> tuple[str, str, str]:
    runtime = resolve_torch_runtime(device)
    return runtime.torch_device, runtime.backend_kind, runtime.device_display_name


def resolve_torch_device(device: str = "auto") -> tuple[str, str]:
    runtime = resolve_torch_runtime(device)
    return runtime.torch_device, runtime.device_display_name


def synchronize_torch_device(device: str, backend_kind: str | None = None) -> None:
    if torch is None:
        return
    normalized_device = str(device).strip().lower()
    normalized_backend = str(backend_kind).strip().lower() if backend_kind is not None else ""
    if normalized_device == "cuda" and normalized_backend in {"", "cuda", "hip"}:
        torch.cuda.synchronize()


def build_torch_dataset(
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
    device: str = "cuda",
    chunk_size: int = 1024,
) -> dict[str, Any]:
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")

    runtime = resolve_torch_runtime(device)
    device_name = runtime.torch_device
    gen = torch.Generator(device=device_name)
    gen.manual_seed(int(seed))
    n = int(n_samples)
    temp = torch.rand(n, generator=gen, device=device_name, dtype=torch.float32) * 150.0 + 250.0
    vdd = torch.rand(n, generator=gen, device=device_name, dtype=torch.float32) * 0.6 + 0.6
    cell_ratio = torch.rand(n, generator=gen, device=device_name, dtype=torch.float32) * 3.0 + 1.0
    width = torch.rand(n, generator=gen, device=device_name, dtype=torch.float32) * 1.9 + 0.1
    length = torch.rand(n, generator=gen, device=device_name, dtype=torch.float32) * 0.135 + 0.045

    vth_nom = 0.40
    a_vt = 0.005
    wl = torch.clamp(width * length, min=1e-12)
    sigma_vth = a_vt / torch.sqrt(wl)

    snm_mean_chunks = []
    snm_std_chunks = []
    chunk = max(int(chunk_size), 1)
    for start in range(0, n, chunk):
        end = min(start + chunk, n)
        chunk_sigma = torch.clamp(sigma_vth[start:end], min=0.0).view(-1, 1, 1)
        sampled_vth = torch.normal(
            mean=torch.full((end - start, int(variability_samples), 6), float(vth_nom), device=device_name),
            std=chunk_sigma.expand(end - start, int(variability_samples), 6),
            generator=gen,
        )
        effective_vth = sampled_vth.mean(dim=2)
        vdd_chunk = vdd[start:end].view(-1, 1)
        cr_chunk = cell_ratio[start:end].view(-1, 1)
        denominator = 1.0 + cr_chunk + 2.0 * cr_chunk * (effective_vth / torch.clamp(vdd_chunk, min=1e-12))
        snm_samples = torch.clamp(
            (vdd_chunk - 2.0 * effective_vth) * cr_chunk / torch.clamp(denominator, min=1e-12),
            min=0.0,
        )
        snm_mean_chunks.append(torch.mean(snm_samples, dim=1))
        snm_std_chunks.append(torch.std(snm_samples, dim=1, unbiased=True))

    snm_mean = torch.cat(snm_mean_chunks, dim=0)
    snm_std = torch.cat(snm_std_chunks, dim=0)
    noise_sigma = torch.sqrt(torch.clamp(1.38e-23 * temp / 5e-15, min=1e-18))
    denom = torch.sqrt(torch.clamp(snm_std**2 + noise_sigma**2, min=1e-18))
    q = -snm_mean / denom
    ber = 0.5 * (1.0 + torch.erf(q / np.sqrt(2.0)))
    ber = torch.clamp(ber, 0.0, 1.0)
    x = torch.stack([temp, vdd, cell_ratio, width, length], dim=1)
    return {"X": x, "snm": snm_mean, "ber": ber, "noise_sigma": noise_sigma}


def export_perceptron_to_torch(model: Any, *, device: str = "cuda") -> TorchExportedPerceptron:
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")

    runtime = resolve_torch_runtime(device)
    device_name = runtime.torch_device
    return TorchExportedPerceptron(
        device=device_name,
        backend_kind=runtime.backend_kind,
        runtime_kind=runtime.runtime_kind,
        device_display_name=runtime.device_display_name,
        x_mean=torch.tensor(model.x_mean_, dtype=torch.float32, device=device_name),
        x_std=torch.tensor(model.x_std_, dtype=torch.float32, device=device_name),
        y_mean=float(model.y_mean_),
        y_std=float(model.y_std_),
        w1=torch.tensor(model.W1_, dtype=torch.float32, device=device_name),
        b1=torch.tensor(model.b1_, dtype=torch.float32, device=device_name),
        w2=torch.tensor(model.W2_, dtype=torch.float32, device=device_name),
        b2=float(model.b2_),
    )


def perceptron_predict_torch(exported: TorchExportedPerceptron, x_tensor: Any) -> Any:
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")
    x_norm = (x_tensor - exported.x_mean) / exported.x_std
    hidden = torch.tanh(x_norm @ exported.w1 + exported.b1)
    y_norm = hidden @ exported.w2 + exported.b2
    return y_norm.reshape(-1) * exported.y_std + exported.y_mean
