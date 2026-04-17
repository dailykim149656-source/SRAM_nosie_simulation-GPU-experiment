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

from backends.base import BackendCapability
from backends import runtime_torch_kernels
from backends.registry import get_runtime_backend_capabilities
from backends.torch_portable import torch_accelerator_info
from execution_policy import select_engine


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
    capabilities: Optional[List[BackendCapability]] = None,
) -> Dict[str, Any]:
    out = dict(response)
    out["_exec"] = {
        "selected": selected,
        "reason": reason,
        "work_size": int(work_size),
        "gpu_available": bool(gpu_available),
        "fallback": bool(fallback),
    }
    if capabilities is not None:
        out["_exec"]["capabilities"] = [
            {
                "name": cap.name,
                "device": cap.device,
                "available": bool(cap.available),
                "reason": cap.reason,
                "fallback_allowed": bool(cap.fallback_allowed),
                "precision": cap.precision,
            }
            for cap in capabilities
        ]
    return out


def _attach_exec_meta_rows(
    rows: List[Dict[str, Any]],
    selected: str,
    reason: str,
    work_size: int,
    gpu_available: bool,
    fallback: bool,
    capabilities: Optional[List[BackendCapability]] = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    exec_meta = {
        "selected": selected,
        "reason": reason,
        "work_size": int(work_size),
        "gpu_available": bool(gpu_available),
        "fallback": bool(fallback),
    }
    if capabilities is not None:
        exec_meta["capabilities"] = [
            {
                "name": cap.name,
                "device": cap.device,
                "available": bool(cap.available),
                "reason": cap.reason,
                "fallback_allowed": bool(cap.fallback_allowed),
                "precision": cap.precision,
            }
            for cap in capabilities
        ]
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


def _torch_backend_reason_label(backend_kind: str) -> str:
    return "torch_hip_backend" if str(backend_kind).strip().lower() == "hip" else "torch_cuda_backend"


def _runtime_capabilities(problem_kind: str) -> List[BackendCapability]:
    return get_runtime_backend_capabilities(problem_kind, native_module=_load_native_module())


def _simulate_array_torch_gpu(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return runtime_torch_kernels.simulate_array_torch_accelerated(request)


def _predict_lifetime_torch_gpu(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return runtime_torch_kernels.predict_lifetime_torch_accelerated(request)


def _optimize_design_torch_gpu(request: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    return runtime_torch_kernels.optimize_design_torch_accelerated(request)


def simulate_array(request: Dict[str, Any]) -> Dict[str, Any]:
    """Run SRAM array simulation through native backend if present."""
    selected, reason, work_size, gpu_available = _resolve_engine("simulate", request)
    capabilities = _runtime_capabilities("simulate")
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
            capabilities=capabilities,
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
                    capabilities=capabilities,
                )
            raise NativeBackendError("simulate_array_gpu native response must be a JSON object")

        torch_gpu_response = _simulate_array_torch_gpu(request)
        if torch_gpu_response is not None:
            return _attach_exec_meta(
                torch_gpu_response,
                selected="gpu",
                reason=f"{reason}|{_torch_backend_reason_label(str(torch_gpu_response.get('accelerator_backend', 'cuda')))}",
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=False,
                capabilities=capabilities,
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
                capabilities=capabilities,
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
        capabilities=capabilities,
    )


def predict_lifetime(request: Dict[str, Any]) -> Dict[str, Any]:
    """Run reliability lifetime prediction through native backend if present."""
    selected, reason, work_size, gpu_available = _resolve_engine("lifetime", request)
    capabilities = _runtime_capabilities("lifetime")
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
                    capabilities=capabilities,
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
                reason=f"{reason}|{_torch_backend_reason_label(str(torch_gpu_response.get('accelerator_backend', 'cuda')))}",
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=False,
                capabilities=capabilities,
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
                capabilities=capabilities,
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
        capabilities=capabilities,
    )


def optimize_design(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run design-space optimization through native backend if present."""
    selected, reason, work_size, gpu_available = _resolve_engine("optimize", request)
    capabilities = _runtime_capabilities("optimize")
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
                    capabilities=capabilities,
                )
            raise NativeBackendError("optimize_design_gpu native response must be a JSON list")

        torch_gpu_response = _optimize_design_torch_gpu(request)
        if torch_gpu_response is not None:
            return _attach_exec_meta_rows(
                torch_gpu_response,
                selected="gpu",
                reason=(
                    f"{reason}|{_torch_backend_reason_label(str(torch_gpu_response[0].get('accelerator_backend', 'cuda')))}"
                    if torch_gpu_response
                    else f"{reason}|torch_cuda_backend"
                ),
                work_size=work_size,
                gpu_available=gpu_available,
                fallback=False,
                capabilities=capabilities,
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
                capabilities=capabilities,
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
        capabilities=capabilities,
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
