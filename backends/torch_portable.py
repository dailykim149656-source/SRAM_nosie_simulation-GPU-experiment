"""Device-neutral PyTorch helpers for analytical benchmark paths."""

from __future__ import annotations

from dataclasses import dataclass
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
    x_mean: Any
    x_std: Any
    y_mean: float
    y_std: float
    w1: Any
    b1: Any
    w2: Any
    b2: float


def torch_cuda_info() -> tuple[bool, str]:
    available, _, detail = torch_accelerator_info()
    return available, detail


def torch_accelerator_info() -> tuple[bool, str, str]:
    force_cpu = os.environ.get("SRAM_FORCE_CPU", "").strip().lower() in {"1", "true", "yes"}
    if force_cpu:
        return False, "cpu", "forced_cpu_env"
    if torch is None:
        return False, "cpu", "torch-unavailable"
    if not bool(torch.cuda.is_available()):
        return False, "cpu", "cuda-unavailable"

    hip_version = getattr(getattr(torch, "version", None), "hip", None)
    backend_kind = "hip" if hip_version else "cuda"
    return True, backend_kind, str(torch.cuda.get_device_name(0))


def resolve_torch_accelerator(device: str = "auto") -> tuple[str, str, str]:
    requested = str(device).strip().lower() or "auto"
    if requested == "cpu":
        return "cpu", "cpu", "cpu"

    force_cpu = os.environ.get("SRAM_FORCE_CPU", "").strip().lower() in {"1", "true", "yes"}
    if force_cpu:
        if requested == "auto":
            return "cpu", "cpu", "cpu"
        raise RuntimeError("Accelerator-capable PyTorch is unavailable (forced_cpu_env)")

    if torch is None:
        if requested == "auto":
            return "cpu", "cpu", "cpu"
        raise RuntimeError("PyTorch is unavailable")

    if requested in {"auto", "gpu", "accelerator", "cuda", "hip"}:
        if bool(torch.cuda.is_available()):
            hip_version = getattr(getattr(torch, "version", None), "hip", None)
            backend_kind = "hip" if hip_version else "cuda"
            return "cuda", backend_kind, str(torch.cuda.get_device_name(0))
        if requested == "auto":
            return "cpu", "cpu", "cpu"
        raise RuntimeError("Accelerator-capable PyTorch is unavailable")

    return requested, requested, requested


def resolve_torch_device(device: str = "auto") -> tuple[str, str]:
    torch_device, _, display_name = resolve_torch_accelerator(device)
    return torch_device, display_name


def synchronize_torch_device(device: str) -> None:
    if torch is None:
        return
    if str(device).strip().lower() == "cuda":
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

    device_name, _ = resolve_torch_device(device)
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

    device_name, _ = resolve_torch_device(device)
    return TorchExportedPerceptron(
        device=device_name,
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
