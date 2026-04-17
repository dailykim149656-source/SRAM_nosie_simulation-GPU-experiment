"""Python orchestration layer for native SRAM backends.

This module keeps the UI and workflow in Python while delegating heavy
numerical kernels to a native extension when available.
"""

from __future__ import annotations

import importlib
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from execution_policy import select_engine

try:
    import torch
except Exception:  # pragma: no cover - optional dependency
    torch = None  # type: ignore[assignment]


class NativeBackendError(RuntimeError):
    """Raised when a native backend call fails."""


_NATIVE_MODULE: Optional[Any] = None
_NATIVE_IMPORT_ERROR: Optional[str] = None


def _native_import_error_suffix() -> str:
    if not _NATIVE_IMPORT_ERROR:
        return ""
    return f" (import error: {_NATIVE_IMPORT_ERROR})"


def _load_native_module() -> Optional[Any]:
    global _NATIVE_MODULE, _NATIVE_IMPORT_ERROR
    if _NATIVE_MODULE is not None:
        return _NATIVE_MODULE

    try:
        _NATIVE_MODULE = importlib.import_module("_sram_native")
        _NATIVE_IMPORT_ERROR = None
        return _NATIVE_MODULE
    except Exception as exc:
        _NATIVE_IMPORT_ERROR = f"{exc.__class__.__name__}: {exc}"
        return None


def _json_call(function_name: str, request: Dict[str, Any]) -> Optional[Any]:
    native = _load_native_module()
    if native is None or not hasattr(native, function_name):
        return None

    payload = json.dumps(request, separators=(",", ":"), ensure_ascii=True)
    raw = getattr(native, function_name)(payload)
    if not isinstance(raw, str):
        raise NativeBackendError(f"Native function {function_name} returned non-string response")

    response = json.loads(raw)
    if isinstance(response, dict) and "error" in response:
        raise NativeBackendError(f"Native {function_name} failed: {response['error']}")
    return response


def _native_required(request: Dict[str, Any]) -> bool:
    request_flag = bool(request.get("require_native", False))
    env_flag = os.environ.get("SRAM_REQUIRE_NATIVE", "").strip().lower() in {"1", "true", "yes"}
    return request_flag or env_flag


def _gpu_required(request: Dict[str, Any]) -> bool:
    request_flag = bool(request.get("require_gpu", False))
    env_flag = os.environ.get("SRAM_REQUIRE_GPU", "").strip().lower() in {"1", "true", "yes"}
    return request_flag or env_flag


def _enforce_gpu_requirement(
    request: Dict[str, Any],
    *,
    selected: str,
    reason: str,
    operation_name: str,
) -> None:
    if _gpu_required(request) and selected != "gpu":
        raise NativeBackendError(
            f"GPU backend is required for {operation_name}, but execution policy selected "
            f"{selected} ({reason})."
        )


def _attach_exec_meta(
    response: Dict[str, Any],
    selected: str,
    reason: str,
    work_size: int,
    gpu_available: bool,
    fallback: bool,
) -> Dict[str, Any]:
    out = dict(response)
    out["_exec"] = {
        "selected": selected,
        "reason": reason,
        "work_size": int(work_size),
        "gpu_available": bool(gpu_available),
        "fallback": bool(fallback),
    }
    return out


def _attach_exec_meta_rows(
    rows: List[Dict[str, Any]],
    selected: str,
    reason: str,
    work_size: int,
    gpu_available: bool,
    fallback: bool,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    exec_meta = {
        "selected": selected,
        "reason": reason,
        "work_size": int(work_size),
        "gpu_available": bool(gpu_available),
        "fallback": bool(fallback),
    }
    for row in rows:
        row_out = dict(row)
        row_out["_exec"] = dict(exec_meta)
        out.append(row_out)
    return out


def _normalize_lifetime_response(
    response: Dict[str, Any],
    request: Dict[str, Any],
    *,
    default_backend: str,
) -> Dict[str, Any]:
    out = dict(response)
    out.setdefault("backend", default_backend)

    duty_cycle = float(out.get("duty_cycle", request.get("duty_cycle", 0.5)))
    accepted_failure_rate = float(
        out.get("accepted_failure_rate", request.get("failure_rate", 0.01))
    )
    out["duty_cycle"] = duty_cycle
    out["accepted_failure_rate"] = accepted_failure_rate

    if "lifetime_at_failure_rate" not in out:
        mean_lifetime = float(out.get("mean_lifetime", 0.0))
        target_reliability = max(1.0 - accepted_failure_rate, 1e-12)
        out["lifetime_at_failure_rate"] = mean_lifetime * (
            -math.log(target_reliability)
        ) ** 0.5

    return out


def _resolve_engine(problem_kind: str, request: Dict[str, Any]) -> Tuple[str, str, int, bool]:
    return select_engine(problem_kind=problem_kind, request=request)


def _torch_cuda_available() -> bool:
    return torch is not None and bool(torch.cuda.is_available())


def _torch_randn(shape: Tuple[int, ...], *, generator: Any, device: str, dtype: Any) -> Any:
    return torch.randn(shape, generator=generator, device=device, dtype=dtype)


def _normalize_input_data(input_data: List[Any], num_cells: int) -> List[int]:
    if not input_data:
        return [i % 2 for i in range(num_cells)]
    normalized = [1 if int(bit) > 0 else 0 for bit in list(input_data)[:num_cells]]
    if len(normalized) < num_cells:
        normalized.extend(i % 2 for i in range(len(normalized), num_cells))
    return normalized


def _torch_perceptron_noise_weight(temperature: float, voltage: float, *, device: str, dtype: Any) -> Any:
    norm_temp = torch.tensor((temperature - 310.0) / 30.0, device=device, dtype=dtype)
    norm_volt = torch.tensor((voltage - 1.0) / 0.15, device=device, dtype=dtype)
    z = 0.7 * norm_temp - 0.9 * norm_volt
    return torch.sigmoid(z)


def _torch_thermal_noise_sigma(temperature: float, voltage: float, *, device: str, dtype: Any) -> Any:
    k_b = torch.tensor(1.38e-23, device=device, dtype=dtype)
    cap = torch.tensor(5e-15, device=device, dtype=dtype)
    temp_t = torch.tensor(temperature, device=device, dtype=dtype)
    sigma = torch.sqrt(k_b * temp_t / cap)
    voltage_factor = torch.clamp(torch.tensor(1.0 / max(voltage, 1e-12), device=device, dtype=dtype), min=0.5)
    return sigma * voltage_factor


def _simulate_array_torch_gpu(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not _torch_cuda_available():
        return None

    device = "cuda"
    dtype = torch.float64
    backend = str(request.get("backend", "standard")).strip().lower()
    temperature = float(request.get("temperature", 310.0))
    voltage = float(request.get("voltage", 1.0))
    num_cells = max(1, int(request.get("num_cells", 32)))
    input_data = _normalize_input_data(list(request.get("input_data", [])), num_cells)
    noise_enable = bool(request.get("noise_enable", True))
    variability_enable = bool(request.get("variability_enable", True))
    monte_carlo_runs = max(1, int(request.get("monte_carlo_runs", 10)))
    width = float(request.get("width", 1.0))
    length = float(request.get("length", 1.0))
    include_thermal_noise = bool(request.get("include_thermal_noise", True))
    seed = int(request.get("seed", 0x5A17_2026))

    generator = torch.Generator(device=device)
    generator.manual_seed(seed)
    input_tensor = torch.tensor(input_data, device=device, dtype=dtype).view(1, num_cells)
    target_bits = input_tensor.expand(monte_carlo_runs, num_cells)
    sigma_vth = float(5.0 / max(width * length, 1e-12) ** 0.5 / 1000.0)
    thermal_sigma = _torch_thermal_noise_sigma(temperature, voltage, device=device, dtype=dtype)

    if backend == "hybrid":
        temp_factor = 1.0 + (temperature - 300.0) / 300.0 * 0.1
        volt_factor = voltage / 1.0
        drive_factor = max(temp_factor * volt_factor, 0.05)
        gate_noise = torch.tensor(0.0, device=device, dtype=dtype)
        if noise_enable:
            mlp_noise_weight = _torch_perceptron_noise_weight(temperature, voltage, device=device, dtype=dtype)
            base_noise = 0.05 * (1.0 + mlp_noise_weight)
            temp_scale = (temperature - 273.15) / 100.0
            volt_scale = (1.0 - voltage) / 1.0
            gate_noise = base_noise * (1.0 + 0.5 * temp_scale) * (1.0 + 0.3 * volt_scale)
            if include_thermal_noise:
                thermal_noise = (1.38e-23 * temperature) ** 0.5 * 1e10
                gate_noise = gate_noise + thermal_noise * 0.01 + thermal_sigma * 0.1
            gate_noise = torch.clamp(gate_noise, min=0.0)

        mismatch_sigma = max(sigma_vth * 6.0, 0.0) if variability_enable else 0.0
        inv1_w = torch.full((monte_carlo_runs, num_cells), -0.1149, device=device, dtype=dtype)
        inv1_b = torch.full((monte_carlo_runs, num_cells), 0.0514, device=device, dtype=dtype)
        inv2_w = torch.full((monte_carlo_runs, num_cells), -0.1149, device=device, dtype=dtype)
        inv2_b = torch.full((monte_carlo_runs, num_cells), 0.0514, device=device, dtype=dtype)
        access_w1 = torch.full((monte_carlo_runs, num_cells), 0.1909, device=device, dtype=dtype)
        access_w2 = torch.full((monte_carlo_runs, num_cells), 0.1038, device=device, dtype=dtype)
        access_b = torch.full((monte_carlo_runs, num_cells), -0.2434, device=device, dtype=dtype)

        inv1_w = inv1_w + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * 0.0490
        inv1_b = inv1_b + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * 0.0312
        inv2_w = inv2_w + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * 0.0490
        inv2_b = inv2_b + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * 0.0312
        access_w1 = access_w1 + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * 0.0539
        access_w2 = access_w2 + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * 0.0401
        access_b = access_b + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * 0.0612

        if variability_enable and mismatch_sigma > 0.0:
            inv1_w = inv1_w + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * mismatch_sigma
            inv1_b = inv1_b + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * mismatch_sigma * 0.8
            inv2_w = inv2_w + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * mismatch_sigma
            inv2_b = inv2_b + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * mismatch_sigma * 0.8
            access_w1 = access_w1 + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * mismatch_sigma
            access_w2 = access_w2 + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * mismatch_sigma
            access_b = access_b + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * mismatch_sigma * 1.2

        q = target_bits.clone()
        q_bar = 1.0 - q
        for _ in range(10):
            q_new = ((inv1_w * q_bar + inv1_b) * drive_factor)
            q_bar_new = ((inv2_w * q + inv2_b) * drive_factor)
            if noise_enable:
                q_new = q_new + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * gate_noise
                q_bar_new = q_bar_new + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * gate_noise
            q = (q_new >= 0.0).to(dtype)
            q_bar = (q_bar_new >= 0.0).to(dtype)

        read_value = ((access_w1 + access_w2 * q + access_b) * drive_factor)
        if noise_enable:
            read_value = read_value + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * gate_noise
        output_bits = (read_value >= 0.0).to(dtype)
        run_errors = (output_bits != target_bits).to(dtype).mean(dim=1)

        output_data = output_bits[0].detach().cpu().tolist()
        noise_values = [float(gate_noise.detach().cpu().item()) for _ in range(num_cells)] if noise_enable else [0.0] * num_cells
        snm_values: List[float] = []
        if variability_enable:
            base_snm = 0.2
            temp_degradation = (temperature - 300.0) / 300.0 * 0.25
            volt_degradation = (1.0 - voltage) / 1.0 * 0.5
            nominal_snm = max(base_snm * (1.0 - temp_degradation - volt_degradation), 0.0)
            mismatch = _torch_randn((num_cells,), generator=generator, device=device, dtype=dtype) * (sigma_vth * 0.1)
            snm_values = torch.clamp(torch.full((num_cells,), nominal_snm, device=device, dtype=dtype) + mismatch, min=0.0).detach().cpu().tolist()

        bit_error_rate = float(run_errors.mean().detach().cpu().item())
        ber_std = float(run_errors.std(unbiased=False).detach().cpu().item()) if monte_carlo_runs > 1 else 0.0
        thermal_value = float(thermal_sigma.detach().cpu().item())
        return {
            "backend": "hybrid-torch-gpu",
            "temperature": temperature,
            "voltage": voltage,
            "input_data": input_data,
            "output_data": [float(v) for v in output_data],
            "noise_values": [float(v) for v in noise_values],
            "snm_values": [float(v) for v in snm_values],
            "bit_errors": int(round(bit_error_rate * num_cells)),
            "bit_error_rate": bit_error_rate,
            "ber_std": ber_std,
            "ber_confidence_95": 1.96 * ber_std / max(monte_carlo_runs, 1) ** 0.5,
            "monte_carlo_ber": [float(v) for v in run_errors.detach().cpu().tolist()],
            "thermal_sigma": thermal_value,
            "include_thermal_noise": include_thermal_noise,
            "snm_mean": float(sum(snm_values) / len(snm_values)) if snm_values else 0.0,
            "snm_std": float(torch.tensor(snm_values, dtype=dtype).std(unbiased=False).item()) if snm_values else 0.0,
            "mlp_noise_mean": float(_torch_perceptron_noise_weight(temperature, voltage, device=device, dtype=dtype).detach().cpu().item()),
            "noise_mean": float(sum(noise_values) / len(noise_values)) if noise_values else 0.0,
            "bit_error_rate_percent": bit_error_rate * 100.0,
            "num_cells": num_cells,
        }

    perceptron_weight = _torch_perceptron_noise_weight(temperature, voltage, device=device, dtype=dtype)
    base_noise = 0.05 * (1.0 + perceptron_weight)
    temp_factor = (temperature - 273.15) / 100.0
    volt_factor = max((1.0 - voltage) / 1.0, -0.8)
    total_noise = base_noise * (1.0 + 0.5 * temp_factor) * (1.0 + 0.3 * volt_factor)
    if include_thermal_noise:
        total_noise = total_noise + thermal_sigma * 0.1
    total_noise = torch.clamp(total_noise, min=0.0)

    noise_matrix = torch.full((monte_carlo_runs, num_cells), float(total_noise.detach().cpu().item()), device=device, dtype=dtype)
    if variability_enable:
        noise_matrix = noise_matrix + torch.abs(
            _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype)
        ) * sigma_vth
    if not noise_enable:
        noise_matrix = torch.zeros((monte_carlo_runs, num_cells), device=device, dtype=dtype)

    output = target_bits.clone()
    if noise_enable:
        output = torch.clamp(
            output + _torch_randn((monte_carlo_runs, num_cells), generator=generator, device=device, dtype=dtype) * noise_matrix,
            min=0.0,
            max=1.0,
        )

    run_errors = ((output > 0.5) != (target_bits > 0.5)).to(dtype).mean(dim=1)
    output_data = output[0].detach().cpu().tolist()
    noise_values = noise_matrix[0].detach().cpu().tolist()
    snm_values = []
    if variability_enable:
        delta_vth = _torch_randn((num_cells,), generator=generator, device=device, dtype=dtype) * sigma_vth
        snm_values = torch.abs((torch.tensor(voltage, device=device, dtype=dtype) - 2.0 * (0.4 + delta_vth)) * 0.5).detach().cpu().tolist()

    bit_error_rate = float(run_errors.mean().detach().cpu().item())
    ber_std = float(run_errors.std(unbiased=False).detach().cpu().item()) if monte_carlo_runs > 1 else 0.0
    thermal_value = float(thermal_sigma.detach().cpu().item())
    return {
        "backend": "standard-torch-gpu",
        "temperature": temperature,
        "voltage": voltage,
        "input_data": input_data,
        "output_data": [float(v) for v in output_data],
        "noise_values": [float(v) for v in noise_values],
        "snm_values": [float(v) for v in snm_values],
        "bit_errors": int(round(bit_error_rate * num_cells)),
        "bit_error_rate": bit_error_rate,
        "ber_std": ber_std,
        "ber_confidence_95": 1.96 * ber_std / max(monte_carlo_runs, 1) ** 0.5,
        "monte_carlo_ber": [float(v) for v in run_errors.detach().cpu().tolist()],
        "thermal_sigma": thermal_value,
        "include_thermal_noise": include_thermal_noise,
    }


def _predict_lifetime_torch_gpu(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not _torch_cuda_available():
        return None

    device = "cuda"
    dtype = torch.float64
    temperature = float(request.get("temperature", 330.0))
    vgs = float(request.get("vgs", 1.0))
    vds = float(request.get("vds", 1.0))
    vth = float(request.get("vth", 0.4))
    width = float(request.get("width", 1.0))
    num_cells = max(1, int(request.get("num_cells", 32)))
    failure_threshold = float(request.get("failure_threshold", 0.1))
    duty_cycle = float(request.get("duty_cycle", 0.5))
    failure_rate = float(request.get("failure_rate", 0.01))
    seed = int(request.get("seed", 0xC0DE_2026))

    generator = torch.Generator(device=device)
    generator.manual_seed(seed)
    jitter = _torch_randn((num_cells,), generator=generator, device=device, dtype=dtype)
    width_jitter = torch.clamp(1.0 + jitter * 0.03, min=0.5, max=1.5)
    effective_width = torch.tensor(width, device=device, dtype=dtype) * width_jitter

    t_min = torch.ones(num_cells, device=device, dtype=dtype)
    t_max = torch.full((num_cells,), 3.15e9, device=device, dtype=dtype)
    temperature_t = torch.tensor(temperature, device=device, dtype=dtype)
    vgs_t = torch.tensor(vgs, device=device, dtype=dtype)
    vds_t = torch.tensor(vds, device=device, dtype=dtype)
    vth_t = torch.tensor(vth, device=device, dtype=dtype)
    failure_threshold_t = torch.tensor(failure_threshold, device=device, dtype=dtype)

    for _ in range(50):
        t_mid = 0.5 * (t_min + t_max)
        vgo = torch.clamp(vgs_t - vth_t, min=0.0)
        temp_factor_nbti = torch.exp(torch.tensor(0.12, device=device, dtype=dtype) / (torch.tensor(1.38e-23, device=device, dtype=dtype) * temperature_t / torch.tensor(1.6e-19, device=device, dtype=dtype)))
        nbti = 1e-12 * torch.pow(t_mid, 0.25) * temp_factor_nbti * torch.pow(vgo, 2.0)

        wl_ratio = effective_width
        drain_current = torch.where(
            vds_t > vgo,
            wl_ratio * 500.0 * 1.7e-3 * 0.5 * torch.pow(vgo, 2.0),
            wl_ratio * 500.0 * 1.7e-3 * (vgo * vds_t - torch.pow(vds_t, 2.0) * 0.5),
        )
        id_normalized = drain_current / torch.clamp(effective_width * 1e-6, min=1e-18)
        temp_factor_hci = torch.exp(-torch.tensor(0.20, device=device, dtype=dtype) / (torch.tensor(1.38e-23, device=device, dtype=dtype) * temperature_t / torch.tensor(1.6e-19, device=device, dtype=dtype)))
        hci = -1e-15 * torch.pow(t_mid, 0.33) * temp_factor_hci * torch.pow(torch.clamp(id_normalized, min=0.0), 1.5)
        total_shift = nbti + hci
        snm = 0.2 - 0.05 * torch.abs(total_shift)

        fail_mask = snm < failure_threshold_t
        t_max = torch.where(fail_mask, t_mid, t_max)
        t_min = torch.where(fail_mask, t_min, t_mid)

    lifetime_years = 0.5 * (t_min + t_max) / (365.25 * 24.0 * 3600.0)
    mean_lifetime = float(lifetime_years.mean().detach().cpu().item())
    std_lifetime = float(lifetime_years.std(unbiased=False).detach().cpu().item()) if num_cells > 1 else 0.0
    min_lifetime = float(lifetime_years.min().detach().cpu().item())
    max_lifetime = float(lifetime_years.max().detach().cpu().item())
    scale_param = max(mean_lifetime, 1e-12)
    shape_param = 2.0
    t_90pct = scale_param * ((-torch.log(torch.tensor(0.9, dtype=dtype))).item() ** (1.0 / shape_param))
    t_99pct = scale_param * ((-torch.log(torch.tensor(0.99, dtype=dtype))).item() ** (1.0 / shape_param))
    failure_rate_fit = 1e9 / (scale_param * 365.25 * 24.0)
    return {
        "backend": "torch-gpu",
        "mean_lifetime": mean_lifetime,
        "std_lifetime": std_lifetime,
        "min_lifetime": min_lifetime,
        "max_lifetime": max_lifetime,
        "t_90pct": float(t_90pct),
        "t_99pct": float(t_99pct),
        "failure_rate_fit": float(failure_rate_fit),
        "cell_lifetimes": [float(v) for v in lifetime_years.detach().cpu().tolist()],
        "duty_cycle": duty_cycle,
        "accepted_failure_rate": failure_rate,
    }


def _optimize_design_torch_gpu(request: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    if not _torch_cuda_available():
        return None

    device = "cuda"
    dtype = torch.float64
    workload_cfg = request.get("workload") if isinstance(request.get("workload"), dict) else {}
    hidden_dim = int(workload_cfg.get("hidden_dim", 4096))
    num_layers = int(workload_cfg.get("num_layers", 32))
    num_heads = int(workload_cfg.get("num_heads", 32))
    seq_length = int(workload_cfg.get("seq_length", 2048))
    batch_size = int(workload_cfg.get("batch_size", 1))
    precision = str(workload_cfg.get("precision", "fp16"))
    attention_type = str(workload_cfg.get("attention_type", "standard"))
    num_kv_heads = int(workload_cfg.get("num_kv_heads", num_heads if attention_type != "mqa" else 1) or 0)
    if num_kv_heads <= 0:
        num_kv_heads = num_heads if attention_type != "mqa" else 1
    intermediate_size = int(workload_cfg.get("intermediate_size", 4 * hidden_dim))

    precision_bytes = {
        "fp32": 4.0,
        "fp16": 2.0,
        "bf16": 2.0,
        "fp8": 1.0,
        "int8": 1.0,
        "int4": 0.5,
    }.get(precision, 2.0)
    sparsity_factor = {
        "standard": 1.0,
        "sparse": 0.5,
        "local": 0.3,
    }.get(attention_type, 1.0)
    head_dim = max(hidden_dim // max(num_heads, 1), 1)
    kv_cache_bytes = 2.0 * num_layers * batch_size * seq_length * num_kv_heads * head_dim * precision_bytes
    hidden_states = batch_size * seq_length * hidden_dim * precision_bytes
    attention_scores = batch_size * num_heads * seq_length * seq_length * precision_bytes * sparsity_factor
    ffn_intermediate = batch_size * seq_length * intermediate_size * precision_bytes
    total_memory_bytes = kv_cache_bytes + 2.0 * (hidden_states + attention_scores + ffn_intermediate)
    active_bits = total_memory_bytes * 8.0
    nominal_latency_ms = 1.0 * (num_layers / 32.0) * (hidden_dim / 4096.0) * (seq_length / 2048.0) ** 0.5 / max(batch_size, 1) ** 0.5

    sram_sizes = [float(x) for x in request.get("sram_sizes_mb", [])] or [64.0, 96.0, 128.0, 192.0, 256.0, 384.0, 512.0]
    snm_values = [float(x) for x in request.get("snm_values_mv", [])] or [150.0, 155.0, 160.0, 165.0, 170.0, 175.0, 180.0, 190.0]
    vmin_values = [float(x) for x in request.get("vmin_values_v", [])] or [0.50, 0.55, 0.60, 0.65, 0.70]
    constraints = dict(request.get("constraints", {})) or {}
    max_area = float(constraints.get("max_area_mm2", 100.0))
    max_power = float(constraints.get("max_power_mw", 50.0))
    min_tapout = float(constraints.get("min_tapout_success_prob", 85.0))

    sram_t = torch.tensor(sram_sizes, device=device, dtype=dtype)
    snm_t = torch.tensor(snm_values, device=device, dtype=dtype)
    vmin_t = torch.tensor(vmin_values, device=device, dtype=dtype)
    sram_grid, snm_grid, vmin_grid = torch.meshgrid(sram_t, snm_t, vmin_t, indexing="ij")

    base_ber = torch.tensor(1e-12, device=device, dtype=dtype)
    snm_delta = torch.clamp(175.0 - snm_grid, min=0.0)
    temp_delta = torch.tensor(0.0, device=device, dtype=dtype)
    voltage_delta = torch.clamp(0.70 - vmin_grid, min=0.0)
    ber = torch.clamp(base_ber * torch.pow(10.0, snm_delta / 15.0) * torch.pow(10.0, temp_delta / 40.0) * torch.pow(10.0, voltage_delta / 0.10), max=1.0)
    token_error = torch.where(
        ber < 1e-6,
        torch.clamp(ber * active_bits, max=1.0),
        torch.clamp(1.0 - torch.pow(1.0 - ber, active_bits), max=1.0),
    )
    accuracy_degradation = torch.clamp(token_error * 100.0, max=100.0)
    voltage_penalty = torch.where(
        vmin_grid >= 0.70,
        torch.zeros_like(vmin_grid),
        nominal_latency_ms * (torch.pow(0.70 / torch.clamp(vmin_grid, min=0.4), 2.0) - 1.0),
    )
    tokens_per_sec = torch.where(
        nominal_latency_ms + voltage_penalty > 0.0,
        1000.0 / (nominal_latency_ms + voltage_penalty),
        torch.zeros_like(vmin_grid),
    )

    snm_reduction = torch.clamp(1.0 - (180.0 - snm_grid) / 100.0, min=0.8, max=1.2)
    area_mm2 = sram_grid * 0.05 * snm_reduction
    voltage_ratio = vmin_grid / 0.70
    power_mw = 2.0 * (0.5 * voltage_ratio * voltage_ratio + 0.5 * torch.pow(10.0, (vmin_grid - 0.70) / 0.1))

    snm_margin_sigma = (snm_grid - 160.0) / (3.0 * 5.0)
    risk = torch.where(snm_margin_sigma < 1.0, 25.0 * (1.0 - snm_margin_sigma), torch.zeros_like(snm_grid))
    risk = risk + torch.where(vmin_grid < 0.55, 20.0 * ((0.55 - vmin_grid) / 0.05), torch.zeros_like(vmin_grid))
    risk = risk + torch.where(
        accuracy_degradation > 0.3,
        10.0 * ((accuracy_degradation - 0.3) / (0.5 - 0.3)),
        torch.zeros_like(accuracy_degradation),
    )
    risk = torch.clamp(risk + 5.0, max=95.0)
    tapout_success = 100.0 - risk

    mask = (area_mm2 <= max_area) & (power_mw <= max_power) & (tapout_success >= min_tapout)
    if not bool(mask.any().detach().cpu().item()):
        return []

    indices = torch.nonzero(mask, as_tuple=False)
    candidates: List[Dict[str, Any]] = []
    for idx in indices.detach().cpu().tolist():
        i, j, k = idx
        candidates.append(
            {
                "sram_mb": float(sram_grid[i, j, k].detach().cpu().item()),
                "snm_mv": float(snm_grid[i, j, k].detach().cpu().item()),
                "vmin_v": float(vmin_grid[i, j, k].detach().cpu().item()),
                "area_mm2": float(area_mm2[i, j, k].detach().cpu().item()),
                "power_mw": float(power_mw[i, j, k].detach().cpu().item()),
                "tapout_success_prob": float(tapout_success[i, j, k].detach().cpu().item()),
                "tokens_per_sec": float(tokens_per_sec[i, j, k].detach().cpu().item()),
                "accuracy_degradation": float(accuracy_degradation[i, j, k].detach().cpu().item()),
                "ber": float(ber[i, j, k].detach().cpu().item()),
            }
        )

    pareto: List[Dict[str, Any]] = []
    for i, cand in enumerate(candidates):
        dominated = False
        for j, other in enumerate(candidates):
            if i == j:
                continue
            area_better = other["area_mm2"] <= cand["area_mm2"]
            power_better = other["power_mw"] <= cand["power_mw"]
            success_better = other["tapout_success_prob"] >= cand["tapout_success_prob"]
            strict = (
                other["area_mm2"] < cand["area_mm2"]
                or other["power_mw"] < cand["power_mw"]
                or other["tapout_success_prob"] > cand["tapout_success_prob"]
            )
            if area_better and power_better and success_better and strict:
                dominated = True
                break
        if not dominated:
            pareto.append(cand)

    pareto.sort(key=lambda row: row["area_mm2"])
    return pareto


def simulate_array(request: Dict[str, Any]) -> Dict[str, Any]:
    """Run SRAM array simulation through native backend if present."""
    selected, reason, work_size, gpu_available = _resolve_engine("simulate", request)
    backend = str(request.get("backend", "standard")).strip().lower()
    prefer_hybrid_gate_logic = bool(request.get("prefer_hybrid_gate_logic", False))
    native_required = _native_required(request)
    _enforce_gpu_requirement(
        request,
        selected=selected,
        reason=reason,
        operation_name="simulate_array",
    )

    # Fidelity-first policy for hybrid mode:
    # run the reference Python hybrid path so perceptron gate dynamics are preserved.
    if backend == "hybrid" and prefer_hybrid_gate_logic:
        if _gpu_required(request):
            raise NativeBackendError(
                "GPU backend is required, but hybrid gate-logic reference path is Python-only."
            )
        if native_required:
            raise NativeBackendError(
                "Native backend is required, but hybrid gate-logic reference path is Python-only. "
                "Set prefer_hybrid_gate_logic=false for strict native execution."
            )
        python_response = _simulate_array_python(request)
        return _attach_exec_meta(
            python_response,
            selected="cpu",
            reason=f"{reason}|hybrid_python_reference",
            work_size=work_size,
            gpu_available=gpu_available,
            fallback=True,
        )

    if selected == "gpu":
        gpu_response = _json_call("simulate_array_gpu", request)
        if gpu_response is not None:
            if isinstance(gpu_response, dict):
                return _attach_exec_meta(
                    gpu_response,
                    selected="gpu",
                    reason=reason,
                    work_size=work_size,
                    gpu_available=gpu_available,
                    fallback=False,
                )
            raise NativeBackendError("simulate_array_gpu native response must be a JSON object")

        torch_gpu_response = _simulate_array_torch_gpu(request)
        if torch_gpu_response is not None:
            return _attach_exec_meta(
                torch_gpu_response,
                selected="gpu",
                reason=f"{reason}|torch_cuda_backend",
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=False,
            )

        if _gpu_required(request):
            raise NativeBackendError(
                "GPU backend is required for simulate_array, but no native GPU path is available"
                + _native_import_error_suffix()
            )
        reason = f"{reason}|gpu_path_unavailable_fallback_cpu"

    cpu_native = _json_call("simulate_array", request)
    if cpu_native is not None:
        if isinstance(cpu_native, dict):
            return _attach_exec_meta(
                cpu_native,
                selected="cpu",
                reason=reason if selected == "gpu" else reason,
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=(selected == "gpu"),
            )
        raise NativeBackendError("simulate_array native response must be a JSON object")

    if native_required:
        raise NativeBackendError(
            "Native backend is required, but no native simulate path is available"
            + _native_import_error_suffix()
        )

    python_response = _simulate_array_python(request)
    return _attach_exec_meta(
        python_response,
        selected="cpu",
        reason=f"{reason}|python_fallback",
        work_size=work_size,
        gpu_available=gpu_available,
        fallback=True,
    )


def predict_lifetime(request: Dict[str, Any]) -> Dict[str, Any]:
    """Run reliability lifetime prediction through native backend if present."""
    selected, reason, work_size, gpu_available = _resolve_engine("lifetime", request)
    _enforce_gpu_requirement(
        request,
        selected=selected,
        reason=reason,
        operation_name="predict_lifetime",
    )

    if selected == "gpu":
        gpu_response = _json_call("predict_lifetime_gpu", request)
        if gpu_response is not None:
            if isinstance(gpu_response, dict):
                return _attach_exec_meta(
                    _normalize_lifetime_response(
                        gpu_response,
                        request,
                        default_backend="lifetime-native-gpu",
                    ),
                    selected="gpu",
                    reason=reason,
                    work_size=work_size,
                    gpu_available=gpu_available,
                    fallback=False,
                )
            raise NativeBackendError("predict_lifetime_gpu native response must be a JSON object")

        torch_gpu_response = _predict_lifetime_torch_gpu(request)
        if torch_gpu_response is not None:
            return _attach_exec_meta(
                _normalize_lifetime_response(
                    torch_gpu_response,
                    request,
                    default_backend="lifetime-torch-gpu",
                ),
                selected="gpu",
                reason=f"{reason}|torch_cuda_backend",
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=False,
            )
        if _gpu_required(request):
            raise NativeBackendError(
                "GPU backend is required for predict_lifetime, but no native GPU path is available"
                + _native_import_error_suffix()
            )
        reason = f"{reason}|gpu_path_unavailable_fallback_cpu"

    cpu_native = _json_call("predict_lifetime", request)
    if cpu_native is not None:
        if isinstance(cpu_native, dict):
            return _attach_exec_meta(
                _normalize_lifetime_response(
                    cpu_native,
                    request,
                    default_backend="lifetime-native",
                ),
                selected="cpu",
                reason=reason if selected == "gpu" else reason,
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=(selected == "gpu"),
            )
        raise NativeBackendError("predict_lifetime native response must be a JSON object")

    if _native_required(request):
        raise NativeBackendError(
            "Native backend is required, but no native lifetime path is available"
            + _native_import_error_suffix()
        )

    python_response = _predict_lifetime_python(request)
    return _attach_exec_meta(
        _normalize_lifetime_response(
            python_response,
            request,
            default_backend="lifetime-python",
        ),
        selected="cpu",
        reason=f"{reason}|python_fallback",
        work_size=work_size,
        gpu_available=gpu_available,
        fallback=True,
    )


def optimize_design(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run design-space optimization through native backend if present."""
    selected, reason, work_size, gpu_available = _resolve_engine("optimize", request)
    _enforce_gpu_requirement(
        request,
        selected=selected,
        reason=reason,
        operation_name="optimize_design",
    )

    if selected == "gpu":
        gpu_response = _json_call("optimize_design_gpu", request)
        if gpu_response is not None:
            if isinstance(gpu_response, list):
                return _attach_exec_meta_rows(
                    gpu_response,
                    selected="gpu",
                    reason=reason,
                    work_size=work_size,
                    gpu_available=gpu_available,
                    fallback=False,
                )
            raise NativeBackendError("optimize_design_gpu native response must be a JSON list")

        torch_gpu_response = _optimize_design_torch_gpu(request)
        if torch_gpu_response is not None:
            return _attach_exec_meta_rows(
                torch_gpu_response,
                selected="gpu",
                reason=f"{reason}|torch_cuda_backend",
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=False,
            )
        if _gpu_required(request):
            raise NativeBackendError(
                "GPU backend is required for optimize_design, but no native GPU path is available"
                + _native_import_error_suffix()
            )
        reason = f"{reason}|gpu_path_unavailable_fallback_cpu"

    cpu_native = _json_call("optimize_design", request)
    if cpu_native is not None:
        if isinstance(cpu_native, list):
            return _attach_exec_meta_rows(
                cpu_native,
                selected="cpu",
                reason=reason if selected == "gpu" else reason,
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=(selected == "gpu"),
            )
        raise NativeBackendError("optimize_design native response must be a JSON list")

    if _native_required(request):
        raise NativeBackendError(
            "Native backend is required, but no native optimize path is available"
            + _native_import_error_suffix()
        )

    return _attach_exec_meta_rows(
        _optimize_design_python(request),
        selected="cpu",
        reason=f"{reason}|python_fallback",
        work_size=work_size,
        gpu_available=gpu_available,
        fallback=True,
    )


def _simulate_array_python(request: Dict[str, Any]) -> Dict[str, Any]:
    backend = str(request.get("backend", "standard")).strip().lower()
    temperature = float(request.get("temperature", 310.0))
    voltage = float(request.get("voltage", 1.0))
    num_cells = int(request.get("num_cells", 32))
    input_data = list(request.get("input_data", []))

    if not input_data:
        input_data = [i % 2 for i in range(num_cells)]

    if backend == "hybrid":
        from hybrid_perceptron_sram import HybridSRAMArray

        sram = HybridSRAMArray(
            num_cells=num_cells,
            temperature=temperature,
            voltage=voltage,
        )
        result = sram.simulate(temperature, voltage, input_data)
        result["backend"] = "hybrid-python"
        return result

    from main_advanced import AdvancedSRAMArray

    sram = AdvancedSRAMArray(
        num_cells=num_cells,
        width=float(request.get("width", 1.0)),
        length=float(request.get("length", 1.0)),
    )
    result = sram.simulate(
        temperature=temperature,
        voltage=voltage,
        input_data=input_data,
        noise_enable=bool(request.get("noise_enable", True)),
        variability_enable=bool(request.get("variability_enable", True)),
        monte_carlo_runs=int(request.get("monte_carlo_runs", 10)),
    )
    result["backend"] = "standard-python"
    return result


def _predict_lifetime_python(request: Dict[str, Any]) -> Dict[str, Any]:
    from reliability_model import LifetimePredictor

    predictor = LifetimePredictor(
        num_cells=int(request.get("num_cells", 32)),
        width=float(request.get("width", 1.0)),
    )
    result = predictor.predict_array_lifetime(
        temperature=float(request.get("temperature", 330.0)),
        duty_cycle=float(request.get("duty_cycle", 0.5)),
        failure_rate=float(request.get("failure_rate", 0.01)),
    )
    result["backend"] = "lifetime-python"
    return result


def _optimize_design_python(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    from workload_model import (
        CircuitToSystemTranslator,
        DesignSpaceOptimizer,
        TransformerWorkloadProfile,
        WorkloadScenarios,
    )

    workload_cfg = request.get("workload")
    if isinstance(workload_cfg, dict):
        workload = TransformerWorkloadProfile(
            model_name=str(workload_cfg.get("model_name", "Custom-Workload")),
            hidden_dim=int(workload_cfg.get("hidden_dim", 4096)),
            num_layers=int(workload_cfg.get("num_layers", 32)),
            num_heads=int(workload_cfg.get("num_heads", 32)),
            seq_length=int(workload_cfg.get("seq_length", 2048)),
            batch_size=int(workload_cfg.get("batch_size", 1)),
            precision=str(workload_cfg.get("precision", "fp16")),
            attention_type=str(workload_cfg.get("attention_type", "standard")),
            num_kv_heads=(
                int(workload_cfg["num_kv_heads"])
                if "num_kv_heads" in workload_cfg and workload_cfg["num_kv_heads"] is not None
                else None
            ),
        )
    else:
        workload = WorkloadScenarios.llama_7b_online()

    optimizer = DesignSpaceOptimizer(CircuitToSystemTranslator(workload))

    return optimizer.find_pareto_optimal_designs(
        sram_sizes_mb=[float(x) for x in request.get("sram_sizes_mb", [])] or None,
        snm_values_mv=[float(x) for x in request.get("snm_values_mv", [])] or None,
        vmin_values_v=[float(x) for x in request.get("vmin_values_v", [])] or None,
        constraints=dict(request.get("constraints", {})) or None,
    )
