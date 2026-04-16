"""Execution policy for CPU/GPU engine selection.

Policy goals:
- Keep interactive UX stable (prefer CPU for small jobs)
- Use GPU only for large vectorizable workloads
- Always fall back to CPU when GPU is unavailable
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
import os


CPU_ONLY_KINDS = set()

BASE_WORK_THRESHOLDS = {
    "simulate": 100_000,        # ~1000 cells x 100 MC runs
    "analytical_dataset": 500_000,  # ~1000 samples x 512 variability
    "lifetime": 16_000,         # ~32 cells x 500 margin
    "optimize": 1_000,          # ~10 x 10 x 10 design points
}

INTERACTIVE_THRESHOLD_MULTIPLIER = 2


def detect_gpu_available() -> bool:
    """Detect whether CUDA-capable GPU is available for compute."""
    force_cpu = os.environ.get("SRAM_FORCE_CPU", "").strip().lower()
    if force_cpu in {"1", "true", "yes"}:
        return False

    try:
        import torch  # type: ignore

        if bool(torch.cuda.is_available()):
            return True
    except Exception:
        pass

    try:
        import cupy  # type: ignore

        return int(cupy.cuda.runtime.getDeviceCount()) > 0
    except Exception:
        return False


def estimate_work_size(problem_kind: str, request: Dict[str, Any]) -> int:
    """Estimate computational work for coarse engine selection."""
    if problem_kind == "simulate":
        num_cells = max(1, int(request.get("num_cells", 32)))
        monte_carlo_runs = max(1, int(request.get("monte_carlo_runs", 10)))
        return num_cells * monte_carlo_runs

    if problem_kind == "analytical_dataset":
        n_samples = max(1, int(request.get("n_samples", 5000)))
        variability_samples = max(1, int(request.get("variability_samples", 512)))
        return n_samples * variability_samples

    if problem_kind == "lifetime":
        num_cells = max(1, int(request.get("num_cells", 32)))
        safety_margin = max(1, int(request.get("safety_margin", 500)))
        return num_cells * safety_margin

    if problem_kind == "optimize":
        sram_sizes = request.get("sram_sizes_mb", [])
        snm_values = request.get("snm_values_mv", [])
        vmin_values = request.get("vmin_values_v", [])

        try:
            n_sram = len(sram_sizes)
        except Exception:
            n_sram = 1
        try:
            n_snm = len(snm_values)
        except Exception:
            n_snm = 1
        try:
            n_vmin = len(vmin_values)
        except Exception:
            n_vmin = 1

        n_sram = max(1, int(n_sram))
        n_snm = max(1, int(n_snm))
        n_vmin = max(1, int(n_vmin))
        return n_sram * n_snm * n_vmin

    return 1


def select_engine(problem_kind: str, request: Dict[str, Any]) -> Tuple[str, str, int, bool]:
    """Return (selected_engine, reason, work_size, gpu_available)."""
    compute_mode = str(request.get("compute_mode", "auto")).strip().lower()
    latency_mode = str(request.get("latency_mode", "interactive")).strip().lower()
    if compute_mode not in {"auto", "cpu", "gpu"}:
        compute_mode = "auto"

    gpu_available = detect_gpu_available()
    work_size = estimate_work_size(problem_kind, request)

    if compute_mode == "cpu":
        return "cpu", "forced_cpu", work_size, gpu_available

    if compute_mode == "gpu":
        if problem_kind in CPU_ONLY_KINDS:
            return "cpu", "forced_gpu_but_cpu_only_problem", work_size, gpu_available
        if not gpu_available:
            return "cpu", "forced_gpu_but_no_gpu", work_size, gpu_available
        return "gpu", "forced_gpu", work_size, gpu_available

    if problem_kind in CPU_ONLY_KINDS:
        return "cpu", "cpu_only_problem", work_size, gpu_available

    if not gpu_available:
        return "cpu", "no_gpu_detected", work_size, gpu_available

    threshold = BASE_WORK_THRESHOLDS.get(problem_kind, 10**18)
    if latency_mode == "interactive":
        threshold *= INTERACTIVE_THRESHOLD_MULTIPLIER

    if work_size < threshold:
        return "cpu", f"small_workload_lt_{threshold}", work_size, gpu_available

    return "gpu", f"large_workload_gte_{threshold}", work_size, gpu_available
