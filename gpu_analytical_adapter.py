"""PyTorch-backed analytical dataset + surrogate inference helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from analytical_ground_truth import AnalyticalSRAMModel
from ml_benchmark import TwoLayerPerceptronRegressor

try:
    import torch
except Exception:  # pragma: no cover - optional dependency
    torch = None  # type: ignore


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
    if torch is None:
        return False, "torch-unavailable"
    if not bool(torch.cuda.is_available()):
        return False, "cuda-unavailable"
    return True, str(torch.cuda.get_device_name(0))


def build_numpy_dataset(
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
) -> dict[str, np.ndarray]:
    model = AnalyticalSRAMModel(random_state=seed)
    data = model.generate_dataset(
        n_samples=int(n_samples),
        random_state=int(seed),
        variability_samples=int(variability_samples),
    )
    x = np.column_stack(
        [
            data["temperature"],
            data["voltage"],
            data["cell_ratio"],
            data["width"],
            data["length"],
        ]
    ).astype(float)
    return {
        "X": x,
        "snm": np.asarray(data["snm_mean"], dtype=float),
        "ber": np.asarray(data["ber"], dtype=float),
        "noise_sigma": np.asarray(data["noise_sigma"], dtype=float),
    }


def build_chunked_numpy_dataset(
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
    chunk_size: int = 1024,
) -> dict[str, np.ndarray]:
    model = AnalyticalSRAMModel(random_state=seed)
    rng = np.random.default_rng(seed)

    temp = rng.uniform(250.0, 400.0, size=n_samples)
    vdd = rng.uniform(0.6, 1.2, size=n_samples)
    cell_ratio = rng.uniform(1.0, 4.0, size=n_samples)
    width = rng.uniform(0.1, 2.0, size=n_samples)
    length = rng.uniform(0.045, 0.18, size=n_samples)

    sigma_vth = model.pelgrom_sigma_vth(width, length)
    snm_mean = np.empty(n_samples, dtype=float)
    snm_std = np.empty(n_samples, dtype=float)

    for start in range(0, n_samples, max(int(chunk_size), 1)):
        end = min(start + max(int(chunk_size), 1), n_samples)
        sampled_vth = rng.normal(
            loc=model.vth_nom,
            scale=np.maximum(sigma_vth[start:end].reshape(-1, 1, 1), 0.0),
            size=(end - start, int(variability_samples), 6),
        )
        effective_vth = np.mean(sampled_vth, axis=2)
        chunk_snm = model.seevinck_snm(vdd[start:end].reshape(-1, 1), effective_vth, cell_ratio[start:end].reshape(-1, 1))
        snm_mean[start:end] = np.mean(chunk_snm, axis=1)
        snm_std[start:end] = np.std(chunk_snm, axis=1, ddof=1)

    noise_sigma = np.asarray(model.thermal_noise_sigma(temp), dtype=float)
    ber = np.asarray(model.analytical_ber(snm_mean, snm_std, noise_sigma), dtype=float)
    x = np.column_stack([temp, vdd, cell_ratio, width, length]).astype(float)
    return {
        "X": x,
        "snm": snm_mean,
        "ber": ber,
        "noise_sigma": noise_sigma,
    }


def build_torch_dataset(
    *,
    n_samples: int,
    variability_samples: int,
    seed: int,
    device: str = "cuda",
    chunk_size: int = 1024,
) -> dict[str, Any]:
    available, _ = torch_cuda_info()
    if not available or torch is None:
        raise RuntimeError("CUDA-capable PyTorch is unavailable")

    gen = torch.Generator(device=device)
    gen.manual_seed(int(seed))
    n = int(n_samples)
    temp = torch.rand(n, generator=gen, device=device, dtype=torch.float32) * 150.0 + 250.0
    vdd = torch.rand(n, generator=gen, device=device, dtype=torch.float32) * 0.6 + 0.6
    cell_ratio = torch.rand(n, generator=gen, device=device, dtype=torch.float32) * 3.0 + 1.0
    width = torch.rand(n, generator=gen, device=device, dtype=torch.float32) * 1.9 + 0.1
    length = torch.rand(n, generator=gen, device=device, dtype=torch.float32) * 0.135 + 0.045

    vth_nom = 0.40
    a_vt = 0.005
    wl = torch.clamp(width * length, min=1e-12)
    sigma_vth = a_vt / torch.sqrt(wl)

    snm_mean_chunks = []
    snm_std_chunks = []
    for start in range(0, n, max(int(chunk_size), 1)):
        end = min(start + max(int(chunk_size), 1), n)
        chunk_sigma = torch.clamp(sigma_vth[start:end], min=0.0).view(-1, 1, 1)
        sampled_vth = torch.normal(
            mean=torch.full((end - start, int(variability_samples), 6), float(vth_nom), device=device),
            std=chunk_sigma.expand(end - start, int(variability_samples), 6),
            generator=gen,
        )
        effective_vth = sampled_vth.mean(dim=2)
        vdd_chunk = vdd[start:end].view(-1, 1)
        cr_chunk = cell_ratio[start:end].view(-1, 1)
        denominator = 1.0 + cr_chunk + 2.0 * cr_chunk * (effective_vth / torch.clamp(vdd_chunk, min=1e-12))
        snm_samples = torch.clamp((vdd_chunk - 2.0 * effective_vth) * cr_chunk / torch.clamp(denominator, min=1e-12), min=0.0)
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


def fit_reference_perceptron(
    *,
    n_samples: int = 4096,
    variability_samples: int = 256,
    seed: int = 42,
) -> TwoLayerPerceptronRegressor:
    dataset = build_numpy_dataset(
        n_samples=int(n_samples),
        variability_samples=int(variability_samples),
        seed=int(seed),
    )
    model = TwoLayerPerceptronRegressor(
        hidden_dim=24,
        alpha=5e-2,
        learning_rate=0.005,
        max_iter=4000,
        random_state=int(seed),
    )
    model.fit(dataset["X"], dataset["snm"])
    return model


def perceptron_predict_numpy(model: TwoLayerPerceptronRegressor, x: np.ndarray) -> np.ndarray:
    x_arr = np.asarray(x, dtype=float)
    x_norm = (x_arr - model.x_mean_) / model.x_std_
    hidden = np.tanh(x_norm @ model.W1_ + model.b1_)
    y_norm = hidden @ model.W2_ + model.b2_
    return np.asarray(y_norm, dtype=float).reshape(-1) * model.y_std_ + model.y_mean_


def export_perceptron_to_torch(
    model: TwoLayerPerceptronRegressor,
    *,
    device: str = "cuda",
) -> TorchExportedPerceptron:
    available, _ = torch_cuda_info()
    if not available or torch is None:
        raise RuntimeError("CUDA-capable PyTorch is unavailable")
    return TorchExportedPerceptron(
        device=device,
        x_mean=torch.tensor(model.x_mean_, dtype=torch.float32, device=device),
        x_std=torch.tensor(model.x_std_, dtype=torch.float32, device=device),
        y_mean=float(model.y_mean_),
        y_std=float(model.y_std_),
        w1=torch.tensor(model.W1_, dtype=torch.float32, device=device),
        b1=torch.tensor(model.b1_, dtype=torch.float32, device=device),
        w2=torch.tensor(model.W2_, dtype=torch.float32, device=device),
        b2=float(model.b2_),
    )


def perceptron_predict_torch(exported: TorchExportedPerceptron, x_tensor: Any) -> Any:
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")
    x_norm = (x_tensor - exported.x_mean) / exported.x_std
    hidden = torch.tanh(x_norm @ exported.w1 + exported.b1)
    y_norm = hidden @ exported.w2 + exported.b2
    return y_norm.reshape(-1) * exported.y_std + exported.y_mean

