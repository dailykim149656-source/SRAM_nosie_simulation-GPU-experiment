"""Native-first lifetime helpers shared by UI surfaces."""

from __future__ import annotations

from typing import Any, Dict

from reliability_model import LifetimePredictor

DEFAULT_DUTY_CYCLE = 0.5
DEFAULT_FAILURE_RATE = 0.01

try:
    from native_backend import NativeBackendError, predict_lifetime as native_predict_lifetime
except Exception:  # pragma: no cover - native backend is optional
    NativeBackendError = RuntimeError
    native_predict_lifetime = None  # type: ignore[assignment]


def _python_fallback_lifetime(request: Dict[str, Any], *, reason: str) -> Dict[str, Any]:
    predictor = LifetimePredictor(
        num_cells=int(request.get("num_cells", 32)),
        width=float(request.get("width", 1.0)),
    )
    result = predictor.predict_array_lifetime(
        temperature=float(request.get("temperature", 330.0)),
        duty_cycle=float(request.get("duty_cycle", DEFAULT_DUTY_CYCLE)),
        failure_rate=float(request.get("failure_rate", DEFAULT_FAILURE_RATE)),
    )
    result["backend"] = "lifetime-python-fallback"
    result["runtime_engine"] = "cpu"
    result["fallback_notice"] = reason
    result["_exec"] = {
        "selected": "cpu",
        "reason": reason,
        "work_size": int(request.get("num_cells", 32)) * 500,
        "gpu_available": False,
        "fallback": True,
    }
    return result


def predict_lifetime_native_first(
    *,
    temperature: float,
    width: float,
    num_cells: int,
    duty_cycle: float = DEFAULT_DUTY_CYCLE,
    failure_rate: float = DEFAULT_FAILURE_RATE,
    vgs: float = 1.0,
    vds: float = 1.0,
    vth: float = 0.4,
    compute_mode: str = "auto",
    latency_mode: str = "interactive",
) -> Dict[str, Any]:
    """Prefer the normalized native lifetime path and fall back to Python on failure."""
    request = {
        "temperature": float(temperature),
        "vgs": float(vgs),
        "vds": float(vds),
        "vth": float(vth),
        "width": float(width),
        "num_cells": int(num_cells),
        "duty_cycle": float(duty_cycle),
        "failure_rate": float(failure_rate),
        "compute_mode": str(compute_mode),
        "latency_mode": str(latency_mode),
    }

    if native_predict_lifetime is None:
        return _python_fallback_lifetime(request, reason="native_backend_unavailable")

    try:
        result = native_predict_lifetime(request)
    except Exception as exc:
        exc_name = exc.__class__.__name__
        return _python_fallback_lifetime(request, reason=f"native_failed:{exc_name}")

    if not isinstance(result, dict):
        return _python_fallback_lifetime(request, reason="native_invalid_response")

    exec_meta = result.get("_exec", {})
    if isinstance(exec_meta, dict):
        result.setdefault("runtime_engine", exec_meta.get("selected", "unknown"))
        if bool(exec_meta.get("fallback", False)):
            result.setdefault(
                "fallback_notice",
                f"native_backend_fallback:{exec_meta.get('reason', 'unknown')}",
            )
    else:
        result.setdefault("runtime_engine", "unknown")
    return result


def summarize_lifetime_runtime(result: Dict[str, Any]) -> str:
    """Return a compact source summary for UI surfaces."""
    exec_meta = result.get("_exec", {}) if isinstance(result, dict) else {}
    if not isinstance(exec_meta, dict):
        exec_meta = {}
    backend = result.get("backend", "unknown")
    engine = result.get("runtime_engine", exec_meta.get("selected", "unknown"))
    fallback = bool(exec_meta.get("fallback", False))
    reason = exec_meta.get("reason", "unknown")
    parts = [f"backend={backend}", f"engine={engine}"]
    if fallback:
        parts.append("fallback=yes")
    parts.append(f"reason={reason}")
    return " | ".join(parts)


def build_lifetime_result_text(
    *,
    temperature: float,
    vgs: float,
    vth: float,
    width: float,
    num_cells: int,
    duty_cycle: float,
    failure_rate: float,
    lifetime_result: Dict[str, Any],
    nbti_shift_10y_mv: float,
    hci_shift_10y_mv: float,
    total_shift_10y_mv: float,
) -> str:
    """Build a plain-text lifetime summary for UI surfaces."""
    runtime_summary = summarize_lifetime_runtime(lifetime_result)
    accepted_failure_rate = float(
        lifetime_result.get("accepted_failure_rate", failure_rate)
    )
    target_survival_percent = (1.0 - accepted_failure_rate) * 100.0
    exec_meta = lifetime_result.get("_exec", {})
    if not isinstance(exec_meta, dict):
        exec_meta = {}

    return f"""
=== Reliability Analysis Results ===

Operating Conditions:
---------------------
Temperature:  {temperature} K
Vgs:          {vgs} V
Vth:          {vth} V
Width:        {width} um
Num Cells:    {num_cells}
Duty Cycle:   {duty_cycle:.2f}
Fail Rate:    {accepted_failure_rate:.3f}

Lifetime Prediction:
--------------------
Target Lifetime ({target_survival_percent:.1f}% survival): {lifetime_result['lifetime_at_failure_rate']:.2f} years
Mean Lifetime:     {lifetime_result['mean_lifetime']:.2f} years
Std Deviation:     {lifetime_result['std_lifetime']:.2f} years
Min Lifetime:      {lifetime_result['min_lifetime']:.2f} years
Max Lifetime:      {lifetime_result['max_lifetime']:.2f} years

Reliability Metrics:
--------------------
90% Survival Ref:  {lifetime_result['t_90pct']:.2f} years
99% Survival Ref:  {lifetime_result['t_99pct']:.2f} years
Failure Rate (FIT): {lifetime_result['failure_rate_fit']:.2f} per 10^9 hours

Execution Source:
-----------------
Backend:           {lifetime_result.get('backend', 'unknown')}
Engine:            {lifetime_result.get('runtime_engine', exec_meta.get('selected', 'unknown'))}
Fallback Used:     {exec_meta.get('fallback', 'unknown')}
Dispatch Reason:   {exec_meta.get('reason', 'unknown')}
Summary:           {runtime_summary}

NBTI Impact (at 10 years):
---------------------------
Vth Shift:         {nbti_shift_10y_mv:.2f} mV

HCI Impact (at 10 years):
--------------------------
Vth Shift:         {hci_shift_10y_mv:.2f} mV (decrease)

Net Impact (at 10 years):
--------------------------
Total Vth Shift:   {total_shift_10y_mv:.2f} mV
""".strip()
