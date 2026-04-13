"""SPICE vs native correlation runner.

Phase 1 utility:
- sweep PVT operating points
- collect SPICE-side metrics (ngspice / placeholder / pdk mode)
- collect native simulator metrics
- generate CSV + markdown summary

Note:
The default template is a 6T transistor-level topology with compact level-1
models. Replace model cards and metric equations with foundry/PDK-calibrated
decks for production-quality correlation.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import math
import os
import tempfile
import random
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, pstdev
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from native_backend import simulate_array


CORNER_GAIN = {
    "tt": 1.00,
    "ff": 1.06,
    "ss": 0.94,
    "fs": 1.03,
    "sf": 0.97,
}

DEFAULT_SPICE_PROXY_CONFIG = {
    "snm_scale_mv": 500.0,
    "noise_scale": 1.0,
    "noise_write_weight": 0.5,
    "ber_center_mv": 120.0,
    "ber_slope_mv": 10.0,
}

DATA_SOURCE_CHOICES = (
    "proxy-calibrated",
    "foundry-pdk-pre-silicon",
    "predictive-pdk-pre-silicon",
    "model-card-calibrated",
    "silicon-correlated",
)

SPICE_SOURCE_CHOICES = (
    "ngspice",
    "placeholder",
    "pdk",
)

SIMULATOR_CHOICES = (
    "auto",
    "ngspice",
    "spectre",
    "hspice",
    "xyce",
)
EXTERNAL_SIMULATOR_CHOICES = ("spectre", "hspice", "xyce")

MC_MODE_CHOICES = (
    "off",
    "param_perturb",
    "pdk_mismatch",
)

BER_CONTRACT_MODE_CHOICES = (
    "raw_native",
    "fixed_proxy",
    "native_fit",
)

SNM_NOISE_CONTRACT_MODE_CHOICES = (
    "raw_native",
    "affine_global",
    "affine_corner",
    "affine_corner_temp",
)

DEFAULT_CORNERS_TEXT = "tt,ff,ss"
DEFAULT_TEMPS_K_TEXT = "300,330,360"
DEFAULT_VDDS_TEXT = "0.8,0.9,1.0"
DEFAULT_TEMPLATE_PATH = REPO_ROOT / "spice_validation" / "netlists" / "sram6t_template.sp"
DEFAULT_SPICE_PROXY_CONFIG_PATH = REPO_ROOT / "spice_validation" / "calibration" / "default_spice_proxy.json"
DEFAULT_PDK_REGISTRY_PATH = REPO_ROOT / "spice_validation" / "pdk_registry.json"
DEFAULT_EXTERNAL_SIM_TIMEOUT_SEC = 900

MEASURE_CONTRACT_REVISION = "v3-ber-contract-aligned-2026-02-18"

REQUIRED_MEASURE_PATTERNS = {
    "snm_mv": re.compile(r"MEAS_SNM_MV\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "noise": re.compile(r"MEAS_NOISE\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "ber": re.compile(r"MEAS_BER\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
}

OPTIONAL_MEASURE_PATTERNS = {
    "hold_snm_mv": re.compile(r"MEAS_HOLD_SNM_MV\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "read_snm_mv": re.compile(r"MEAS_READ_SNM_MV\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "write_margin_mv": re.compile(r"MEAS_WRITE_MARGIN_MV\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "noise_sigma": re.compile(r"MEAS_NOISE_SIGMA\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "read_fail": re.compile(r"MEAS_READ_FAIL\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "write_fail": re.compile(r"MEAS_WRITE_FAIL\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
}

MC_DEVICE_NAMES: tuple[str, ...] = ("PU1", "PD1", "PU2", "PD2", "AX1", "AX2")
DEFAULT_MC_MISMATCH_TEMPLATE_VARS: dict[str, str] = {
    f"MC_W_{device}": "1.0" for device in MC_DEVICE_NAMES
}
DEFAULT_MC_MISMATCH_TEMPLATE_VARS.update({f"MC_L_{device}": "1.0" for device in MC_DEVICE_NAMES})
DEFAULT_PDK_MISMATCH_SIGMA_W_REL = 0.03
DEFAULT_PDK_MISMATCH_SIGMA_L_REL = 0.0
DEFAULT_PDK_MISMATCH_CLIP_SIGMA = 3.0

SPICE_RUNTIME_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"Unknown model type\s+psp103va|Unknown model type\s+pspnqs103va", re.IGNORECASE),
        "NGSPICE_UNSUPPORTED_PSP",
        "Use a simulator/build with PSP support (for example Spectre/HSPICE or ngspice with matching PSP model support).",
    ),
    (
        re.compile(r"Only MOS device levels .* are supported.*level\s*=\s*72", re.IGNORECASE | re.DOTALL),
        "NGSPICE_UNSUPPORTED_LEVEL72",
        "Use a simulator/build that supports BSIM-CMG level 72 for ASAP7 decks (for example Spectre/HSPICE).",
    ),
)

CONTROL_BLOCK_RE = re.compile(r"^\s*\.control\b.*?^\s*\.endc\b\s*$", re.IGNORECASE | re.DOTALL | re.MULTILINE)


@dataclass(frozen=True)
class OperatingPoint:
    corner: str
    temp_k: float
    vdd: float

    @property
    def case_id(self) -> str:
        return f"{self.corner}_t{int(round(self.temp_k))}_v{self.vdd:.2f}".replace(".", "p")


@dataclass(frozen=True)
class PdkContext:
    pdk_id: str
    pdk_class: str
    simulator: str
    model_revision: str
    license: str
    model_root: str
    macro_mode: str
    registry_path: str
    config_path: str
    corner_map: dict[str, str]
    template_vars: dict[str, str]
    contract_metric_sources: dict[str, str]
    nmos_corner_pattern: str
    pmos_corner_pattern: str
    mismatch_sigma_w_rel: float
    mismatch_sigma_l_rel: float
    mismatch_clip_sigma: float


def parse_bool_arg(text: str) -> bool:
    token = str(text).strip().lower()
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {text}")


def parse_float_list(text: str) -> list[float]:
    values = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(float(token))
    if not values:
        raise ValueError("at least one numeric value is required")
    return values


def parse_corner_list(text: str) -> list[str]:
    values = []
    for token in text.split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token not in CORNER_GAIN:
            raise ValueError(f"unsupported corner '{token}' (supported: {', '.join(CORNER_GAIN)})")
        values.append(token)
    if not values:
        raise ValueError("at least one corner is required")
    return values


def safe_float(value: object, default: float = float("nan")) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return float(default)
    if math.isfinite(converted):
        return converted
    return float(default)


CONTRACT_RAW_SOURCE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "snm_mv": (
        "spice_snm_mv_raw",
        "spice_hold_snm_mv_raw",
        "spice_read_snm_mv_raw",
    ),
    "hold_snm_mv": (
        "spice_hold_snm_mv_raw",
        "spice_snm_mv_raw",
        "spice_read_snm_mv_raw",
    ),
    "read_snm_mv": ("spice_read_snm_mv_raw",),
    "write_margin_mv": ("spice_write_margin_mv_raw",),
    "noise": ("spice_noise_raw",),
    "noise_sigma": ("spice_noise_sigma_raw", "spice_noise_raw"),
}


def normalize_contract_raw_source(metric_name: str, raw_source_name: str | None) -> str | None:
    if raw_source_name is None:
        return None

    metric_key = str(metric_name).strip()
    candidates = CONTRACT_RAW_SOURCE_CANDIDATES.get(metric_key, ())
    if not candidates:
        return None

    token = str(raw_source_name).strip()
    if not token:
        return None
    if not token.endswith("_raw"):
        token = f"{token}_raw"
    if token in candidates:
        return token
    return None


def parse_contract_metric_sources(
    raw_sources: object,
    *,
    label: str,
) -> dict[str, str]:
    if raw_sources is None or raw_sources == "":
        return {}
    if not isinstance(raw_sources, dict):
        raise ValueError(f"{label} contract_metric_sources must be an object")

    out: dict[str, str] = {}
    for metric_name, raw_source_name in raw_sources.items():
        normalized_metric = str(metric_name).strip()
        normalized_source = normalize_contract_raw_source(normalized_metric, str(raw_source_name))
        if normalized_source is None:
            supported = ", ".join(CONTRACT_RAW_SOURCE_CANDIDATES.get(normalized_metric, ()))
            raise ValueError(
                f"{label} contract source for '{normalized_metric}' is invalid: '{raw_source_name}' "
                f"(supported: {supported or 'n/a'})"
            )
        out[normalized_metric] = normalized_source
    return out


def logistic_failure_from_margin(margin_mv: float, center_mv: float = 50.0, slope_mv: float = 8.0) -> float:
    margin = safe_float(margin_mv)
    if not math.isfinite(margin):
        return float("nan")
    slope = max(abs(float(slope_mv)), 1e-9)
    z = (margin - float(center_mv)) / slope
    if z >= 60.0:
        return 0.0
    if z <= -60.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(z))


def logistic_ber_from_snm(snm_mv: float, center_mv: float, slope_mv: float) -> float:
    snm = safe_float(snm_mv)
    if not math.isfinite(snm):
        return float("nan")
    slope = max(abs(float(slope_mv)), 1e-9)
    z = (snm - float(center_mv)) / slope
    if z >= 60.0:
        return 0.0
    if z <= -60.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(z))


def fit_native_ber_contract_params(
    rows: list[dict[str, float | str | bool]],
    default_center_mv: float,
    default_slope_mv: float,
) -> tuple[float, float, int]:
    x_values: list[float] = []
    y_values: list[float] = []
    clip_eps = 1e-6
    for row in rows:
        snm_mv = safe_float(row.get("native_snm_mv"))
        ber_raw = safe_float(row.get("native_ber_raw"))
        if not math.isfinite(snm_mv) or not math.isfinite(ber_raw):
            continue
        ber_clipped = min(max(ber_raw, clip_eps), 1.0 - clip_eps)
        logit = math.log(ber_clipped / max(1.0 - ber_clipped, clip_eps))
        x_values.append(snm_mv)
        y_values.append(logit)

    n = len(x_values)
    if n < 2:
        return float(default_center_mv), float(default_slope_mv), n

    sx = sum(x_values)
    sy = sum(y_values)
    sxx = sum(v * v for v in x_values)
    sxy = sum(x * y for x, y in zip(x_values, y_values))
    denom = (n * sxx) - (sx * sx)
    if abs(denom) <= 1e-12:
        return float(default_center_mv), float(default_slope_mv), n

    slope_logit = ((n * sxy) - (sx * sy)) / denom
    intercept_logit = (sy - (slope_logit * sx)) / n
    if not math.isfinite(slope_logit) or abs(slope_logit) <= 1e-12:
        return float(default_center_mv), float(default_slope_mv), n

    mapped_slope_mv = -1.0 / slope_logit
    if not math.isfinite(mapped_slope_mv) or mapped_slope_mv <= 1e-6:
        return float(default_center_mv), float(default_slope_mv), n
    mapped_center_mv = intercept_logit * mapped_slope_mv
    if not math.isfinite(mapped_center_mv):
        return float(default_center_mv), float(default_slope_mv), n

    return float(mapped_center_mv), float(mapped_slope_mv), n


def fit_affine_params(
    x_values: list[float],
    y_values: list[float],
) -> tuple[float, float, int]:
    n = min(len(x_values), len(y_values))
    if n < 2:
        return 1.0, 0.0, n
    xs = x_values[:n]
    ys = y_values[:n]
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(v * v for v in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = (n * sxx) - (sx * sx)
    if abs(denom) <= 1e-12:
        return 1.0, 0.0, n
    a = ((n * sxy) - (sx * sy)) / denom
    b = (sy - (a * sx)) / n
    if not math.isfinite(a) or not math.isfinite(b):
        return 1.0, 0.0, n
    return float(a), float(b), n


def metric_group_key(row: dict[str, float | str | bool], contract_mode: str) -> tuple[object, ...]:
    mode = str(contract_mode).strip().lower()
    corner = str(row.get("corner", "")).strip().lower()
    temp_k = round(safe_float(row.get("temp_k"), default=float("nan")), 2)
    if mode == "affine_corner":
        return (corner,)
    if mode == "affine_corner_temp":
        return (corner, temp_k)
    return ("global",)


def metric_raw_span(rows: list[dict[str, float | str | bool]], key: str) -> float:
    finite_values = [
        value
        for value in (safe_float(row.get(key), default=float("nan")) for row in rows)
        if math.isfinite(value)
    ]
    if len(finite_values) < 2:
        return 0.0
    return float(max(finite_values) - min(finite_values))


CONTRACT_RAW_MIN_SPAN_BY_METRIC = {
    "snm_mv": 1.0,
    "hold_snm_mv": 1.0,
    "read_snm_mv": 1.0,
    "write_margin_mv": 1.0,
}


def metric_raw_stats(
    rows: list[dict[str, float | str | bool]],
    key: str,
) -> dict[str, float | int]:
    finite_values = [
        value
        for value in (safe_float(row.get(key), default=float("nan")) for row in rows)
        if math.isfinite(value)
    ]
    if not finite_values:
        return {
            "finite_count": 0,
            "span": 0.0,
        }
    if len(finite_values) == 1:
        return {
            "finite_count": 1,
            "span": 0.0,
        }
    return {
        "finite_count": int(len(finite_values)),
        "span": float(max(finite_values) - min(finite_values)),
    }


def classify_contract_raw_metric(
    *,
    finite_count: int,
    span: float,
    min_span: float,
) -> tuple[bool, str]:
    if finite_count < 2:
        return False, "missing_finite_values"
    if span < min_span:
        return False, "degenerate_span"
    return True, "usable"


def metric_value_span(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(max(values) - min(values))


def apply_snm_noise_contract(
    rows: list[dict[str, float | str | bool]],
    contract_mode: str,
    metric_source_overrides: dict[str, str] | None = None,
    allow_fallback: bool = False,
) -> dict[str, object]:
    mode = str(contract_mode).strip().lower()
    summary: dict[str, object] = {
        "mode": mode,
        "metrics": {},
    }
    if not rows:
        return summary

    metric_specs = (
        ("snm_mv", "spice_snm_mv", "native_snm_mv", "delta_snm_mv"),
        ("hold_snm_mv", "spice_hold_snm_mv", "native_hold_snm_mv", "delta_hold_snm_mv"),
        ("read_snm_mv", "spice_read_snm_mv", "native_read_snm_mv", "delta_read_snm_mv"),
        ("write_margin_mv", "spice_write_margin_mv", "native_write_margin_mv", "delta_write_margin_mv"),
        ("noise", "spice_noise", "native_noise", "delta_noise"),
        ("noise_sigma", "spice_noise_sigma", "native_noise_sigma", "delta_noise_sigma"),
    )

    # Preserve raw spice metrics once.
    for _, spice_key, _, _ in metric_specs:
        raw_key = f"{spice_key}_raw"
        for row in rows:
            if raw_key not in row:
                row[raw_key] = row.get(spice_key, float("nan"))

    fallback_metric_raw_key = "spice_read_snm_mv_raw"
    source_overrides = metric_source_overrides if isinstance(metric_source_overrides, dict) else {}

    if mode == "raw_native":
        for metric_name, spice_key, native_key, delta_key in metric_specs:
            chosen_raw_key = normalize_contract_raw_source(metric_name, source_overrides.get(metric_name))
            source_raw_key = chosen_raw_key or f"{spice_key}_raw"
            for row in rows:
                spice_raw = safe_float(row.get(source_raw_key))
                row[f"{spice_key}_contract"] = spice_raw
                row[spice_key] = spice_raw
                native_val = safe_float(row.get(native_key))
                row[delta_key] = float(native_val) - float(spice_raw)
            summary["metrics"][metric_name] = {
                "global_a": 1.0,
                "global_b": 0.0,
                "global_samples": int(len(rows)),
                "group_count": 1,
                "requested_raw_key": chosen_raw_key or "",
                "source_raw_key": source_raw_key,
                "source_raw_span": metric_raw_span(rows, source_raw_key),
                "source_finite_count": int(metric_raw_stats(rows, source_raw_key)["finite_count"]),
                "fallback_used": False,
                "invalid_raw_metric": False,
                "reason": "raw_native_identity",
                "fit_status": "raw_native_identity",
                "group_fit_fallbacks": 0,
            }
        return summary

    for metric_name, spice_key, native_key, delta_key in metric_specs:
        requested_raw_key = normalize_contract_raw_source(metric_name, source_overrides.get(metric_name))
        primary_raw_key = requested_raw_key or f"{spice_key}_raw"
        source_raw_key = primary_raw_key
        min_span = float(CONTRACT_RAW_MIN_SPAN_BY_METRIC.get(metric_name, 0.0))
        primary_stats = metric_raw_stats(rows, primary_raw_key)
        primary_valid, primary_reason = classify_contract_raw_metric(
            finite_count=int(primary_stats["finite_count"]),
            span=float(primary_stats["span"]),
            min_span=min_span,
        )
        fallback_used = False
        invalid_raw_metric = not primary_valid
        reason = primary_reason if invalid_raw_metric else "usable"
        fit_status = "fitted"

        if metric_name in {"snm_mv", "hold_snm_mv"} and invalid_raw_metric and allow_fallback:
            fallback_stats = metric_raw_stats(rows, fallback_metric_raw_key)
            fallback_valid, _ = classify_contract_raw_metric(
                finite_count=int(fallback_stats["finite_count"]),
                span=float(fallback_stats["span"]),
                min_span=float(CONTRACT_RAW_MIN_SPAN_BY_METRIC.get("read_snm_mv", min_span)),
            )
            if fallback_valid:
                source_raw_key = fallback_metric_raw_key
                fallback_used = True
                if requested_raw_key:
                    reason = "explicit_source_invalid_fallback_to_read_snm"
                else:
                    reason = "fallback_to_read_snm"
                fit_status = "fitted_after_fallback"
        elif invalid_raw_metric and requested_raw_key:
            reason = "explicit_source_invalid"

        source_stats = metric_raw_stats(rows, source_raw_key)
        source_valid, source_reason = classify_contract_raw_metric(
            finite_count=int(source_stats["finite_count"]),
            span=float(source_stats["span"]),
            min_span=min_span,
        )

        global_x: list[float] = []
        global_y: list[float] = []
        grouped_xy: dict[tuple[object, ...], tuple[list[float], list[float]]] = {}
        for row in rows:
            spice_raw = safe_float(row.get(source_raw_key))
            native_val = safe_float(row.get(native_key))
            if not math.isfinite(spice_raw) or not math.isfinite(native_val):
                continue
            global_x.append(spice_raw)
            global_y.append(native_val)
            g_key = metric_group_key(row, mode)
            if g_key not in grouped_xy:
                grouped_xy[g_key] = ([], [])
            grouped_xy[g_key][0].append(spice_raw)
            grouped_xy[g_key][1].append(native_val)

        if source_valid:
            global_a, global_b, global_n = fit_affine_params(global_x, global_y)
        else:
            global_a, global_b, global_n = 1.0, 0.0, int(source_stats["finite_count"])
            fit_status = "skipped_invalid_raw"
            if not fallback_used:
                reason = source_reason
        per_group: dict[tuple[object, ...], tuple[float, float, int]] = {}
        group_fit_fallbacks = 0
        if mode in {"affine_corner", "affine_corner_temp"}:
            for g_key, (gx, gy) in grouped_xy.items():
                if source_valid:
                    group_valid, _ = classify_contract_raw_metric(
                        finite_count=len(gx),
                        span=metric_value_span(gx),
                        min_span=min_span,
                    )
                else:
                    group_valid = False
                if group_valid:
                    g_a, g_b, g_n = fit_affine_params(gx, gy)
                else:
                    g_a, g_b, g_n = global_a, global_b, global_n
                    group_fit_fallbacks += 1
                if g_n < 2:
                    g_a, g_b, g_n = global_a, global_b, global_n
                    group_fit_fallbacks += 1
                per_group[g_key] = (g_a, g_b, g_n)
        else:
            per_group[("global",)] = (global_a, global_b, global_n)

        for row in rows:
            spice_raw = safe_float(row.get(source_raw_key))
            if not math.isfinite(spice_raw):
                row[f"{spice_key}_contract"] = spice_raw
                continue
            g_key = metric_group_key(row, mode)
            if g_key in per_group:
                a, b, _ = per_group[g_key]
            else:
                a, b, _ = global_a, global_b, global_n
            spice_contract = (a * spice_raw) + b
            row[f"{spice_key}_contract"] = float(spice_contract)
            row[spice_key] = float(spice_contract)
            native_val = safe_float(row.get(native_key))
            row[delta_key] = float(native_val) - float(spice_contract)

        summary["metrics"][metric_name] = {
            "global_a": float(global_a),
            "global_b": float(global_b),
            "global_samples": int(global_n),
            "group_count": int(len(per_group)),
            "requested_raw_key": requested_raw_key or "",
            "source_raw_key": source_raw_key,
            "source_raw_span": float(source_stats["span"]),
            "source_finite_count": int(source_stats["finite_count"]),
            "fallback_used": bool(fallback_used),
            "invalid_raw_metric": bool(invalid_raw_metric),
            "reason": reason,
            "fit_status": fit_status,
            "group_fit_fallbacks": int(group_fit_fallbacks),
        }

    # Keep fail-rate metrics coherent with aligned read/write margins.
    for row in rows:
        spice_read_snm = safe_float(row.get("spice_read_snm_mv"))
        spice_write_margin = safe_float(row.get("spice_write_margin_mv"))
        read_fail_contract = logistic_failure_from_margin(spice_read_snm, center_mv=50.0, slope_mv=8.0)
        write_fail_contract = logistic_failure_from_margin(spice_write_margin, center_mv=50.0, slope_mv=8.0)
        row["spice_read_fail_contract"] = read_fail_contract
        row["spice_write_fail_contract"] = write_fail_contract
        row["spice_read_fail"] = read_fail_contract
        row["spice_write_fail"] = write_fail_contract
        native_read_fail = safe_float(row.get("native_read_fail"))
        native_write_fail = safe_float(row.get("native_write_fail"))
        row["delta_read_fail"] = float(native_read_fail) - float(read_fail_contract)
        row["delta_write_fail"] = float(native_write_fail) - float(write_fail_contract)

    metrics_summary = summary.get("metrics", {})
    if isinstance(metrics_summary, dict):
        for row in rows:
            for metric_name, item in metrics_summary.items():
                if not isinstance(item, dict):
                    continue
                row[f"{metric_name}_contract_requested_raw_key"] = str(item.get("requested_raw_key", ""))
                row[f"{metric_name}_contract_source_raw_key"] = str(item.get("source_raw_key", ""))
                row[f"{metric_name}_contract_fallback_used"] = bool(item.get("fallback_used", False))
                row[f"{metric_name}_contract_fit_status"] = str(item.get("fit_status", "n/a"))
                row[f"{metric_name}_contract_reason"] = str(item.get("reason", "n/a"))

    return summary


def load_json_object(path: Path, label: str) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return loaded


def resolve_maybe_relative_path(path_text: str, base_dir: Path) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    from_base = (base_dir / candidate).resolve()
    if from_base.exists():
        return from_base
    return (REPO_ROOT / candidate).resolve()


def normalize_data_source(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = str(text).strip().lower()
    if not normalized:
        return None
    if normalized not in DATA_SOURCE_CHOICES:
        supported = ", ".join(DATA_SOURCE_CHOICES)
        raise ValueError(f"unsupported data source '{text}' (supported: {supported})")
    return normalized


def default_data_source_for_pdk_class(pdk_class: str) -> str:
    class_key = str(pdk_class).strip().lower()
    if class_key == "foundry-open":
        return "foundry-pdk-pre-silicon"
    if class_key == "predictive":
        return "predictive-pdk-pre-silicon"
    if class_key == "model-only":
        return "model-card-calibrated"
    return "foundry-pdk-pre-silicon"


def load_pdk_context(args: argparse.Namespace) -> PdkContext | None:
    if args.spice_source != "pdk":
        return None
    if not args.pdk_id:
        raise ValueError("--pdk-id is required when --spice-source pdk")

    registry_obj = load_json_object(args.pdk_registry, "pdk registry")
    registry_items = registry_obj.get("pdks", [])
    if not isinstance(registry_items, list):
        raise ValueError(f"pdk registry 'pdks' must be a list: {args.pdk_registry}")

    registry_map: dict[str, dict[str, object]] = {}
    for item in registry_items:
        if not isinstance(item, dict):
            continue
        pdk_id = str(item.get("pdk_id", "")).strip().lower()
        if pdk_id:
            registry_map[pdk_id] = item

    requested_pdk_id = str(args.pdk_id).strip().lower()
    if requested_pdk_id not in registry_map:
        supported = ", ".join(sorted(registry_map))
        raise ValueError(f"unknown pdk-id '{requested_pdk_id}' (supported: {supported})")

    entry = registry_map[requested_pdk_id]
    cfg: dict[str, object] = {}
    if args.pdk_config is not None:
        cfg = load_json_object(args.pdk_config, "pdk run config")
        cfg_pdk_id = str(cfg.get("pdk_id", requested_pdk_id)).strip().lower()
        if cfg_pdk_id != requested_pdk_id:
            raise ValueError(
                f"pdk config pdk_id mismatch: expected '{requested_pdk_id}', got '{cfg_pdk_id}'"
            )

    def pick_value(key: str, default: str, cli_value: str | None) -> str:
        if cli_value is not None and str(cli_value).strip():
            return str(cli_value).strip()
        if key in cfg and str(cfg[key]).strip():
            return str(cfg[key]).strip()
        if key in entry and str(entry[key]).strip():
            return str(entry[key]).strip()
        return str(default)

    def pick_float(key: str, default: float) -> float:
        if key in cfg and str(cfg[key]).strip():
            return float(cfg[key])
        if key in entry and str(entry[key]).strip():
            return float(entry[key])
        return float(default)

    def pick_int(key: str, default: int) -> int:
        if key in cfg and str(cfg[key]).strip():
            return int(cfg[key])
        if key in entry and str(entry[key]).strip():
            return int(entry[key])
        return int(default)

    def pick_path(
        key: str,
        default_path: Path,
        cli_value: Path | None,
        cli_base_dir: Path,
    ) -> Path:
        if cli_value is not None:
            return cli_value.resolve()
        if key in cfg and str(cfg[key]).strip():
            return resolve_maybe_relative_path(str(cfg[key]).strip(), cli_base_dir)
        if key in entry and str(entry[key]).strip():
            return resolve_maybe_relative_path(str(entry[key]).strip(), args.pdk_registry.parent)
        return default_path.resolve()

    args.corners = pick_value("corners", DEFAULT_CORNERS_TEXT, args.corners)
    args.temps_k = pick_value("temps_k", DEFAULT_TEMPS_K_TEXT, args.temps_k)
    args.vdds = pick_value("vdds", DEFAULT_VDDS_TEXT, args.vdds)

    picked_data_source = args.data_source
    if picked_data_source is None:
        if "data_source" in cfg:
            picked_data_source = str(cfg["data_source"])
        elif "data_source" in entry:
            picked_data_source = str(entry["data_source"])
        else:
            picked_data_source = default_data_source_for_pdk_class(str(entry.get("pdk_class", "")))
    args.data_source = normalize_data_source(picked_data_source)

    pdk_sim_default = str(entry.get("simulator", "ngspice")).strip().lower()
    if "simulator" in cfg and str(cfg["simulator"]).strip():
        pdk_sim_default = str(cfg["simulator"]).strip().lower()
    if args.simulator == "auto":
        args.simulator = pdk_sim_default
    supported_simulators = {"ngspice", *EXTERNAL_SIMULATOR_CHOICES}
    if args.simulator not in supported_simulators:
        raise RuntimeError(
            f"unsupported pdk simulator '{args.simulator}' "
            f"(supported: {', '.join(sorted(supported_simulators))})"
        )
    if args.simulator in EXTERNAL_SIMULATOR_CHOICES:
        if args.external_sim_cmd is None:
            args.external_sim_cmd = pick_value("external_sim_cmd", "", None)
        if args.external_sim_timeout_sec is None:
            args.external_sim_timeout_sec = pick_int(
                "external_sim_timeout_sec",
                DEFAULT_EXTERNAL_SIM_TIMEOUT_SEC,
            )

    config_base = args.pdk_config.parent if args.pdk_config is not None else args.pdk_registry.parent
    args.template = pick_path("template", DEFAULT_TEMPLATE_PATH, args.template, config_base)
    args.spice_proxy_config = pick_path(
        "spice_proxy_config",
        DEFAULT_SPICE_PROXY_CONFIG_PATH,
        args.spice_proxy_config,
        config_base,
    )

    corner_map_raw: dict[str, object] = {}
    if isinstance(entry.get("corner_map"), dict):
        corner_map_raw.update(entry.get("corner_map", {}))
    if isinstance(cfg.get("corner_map"), dict):
        corner_map_raw.update(cfg.get("corner_map", {}))
    corner_map: dict[str, str] = {}
    for key in CORNER_GAIN:
        mapped = corner_map_raw.get(key, key)
        corner_map[key] = str(mapped).strip()

    contract_metric_sources_raw: dict[str, object] = {}
    if isinstance(entry.get("contract_metric_sources"), dict):
        contract_metric_sources_raw.update(entry.get("contract_metric_sources", {}))
    if isinstance(cfg.get("contract_metric_sources"), dict):
        contract_metric_sources_raw.update(cfg.get("contract_metric_sources", {}))
    contract_metric_sources = parse_contract_metric_sources(
        contract_metric_sources_raw,
        label=f"PDK '{requested_pdk_id}'",
    )

    model_lib_text = ""
    if "model_lib" in entry and str(entry.get("model_lib", "")).strip():
        model_lib_text = str(entry.get("model_lib", "")).strip()
    if "model_lib" in cfg and str(cfg.get("model_lib", "")).strip():
        model_lib_text = str(cfg.get("model_lib", "")).strip()
    if model_lib_text:
        model_lib_path = resolve_maybe_relative_path(model_lib_text, config_base).resolve()
        model_lib_value = model_lib_path.as_posix()
    else:
        model_lib_value = ""

    template_vars_raw: dict[str, object] = {}
    if isinstance(entry.get("template_vars"), dict):
        template_vars_raw.update(entry.get("template_vars", {}))
    if isinstance(cfg.get("template_vars"), dict):
        template_vars_raw.update(cfg.get("template_vars", {}))

    template_vars: dict[str, str] = {}
    for key, value in template_vars_raw.items():
        template_vars[str(key)] = str(value)
    if model_lib_value:
        template_vars["PDK_MODEL_LIB"] = model_lib_value
    if "PDK_NMOS_MODEL" not in template_vars:
        template_vars["PDK_NMOS_MODEL"] = str(cfg.get("nmos_model", entry.get("nmos_model", "nch")))
    if "PDK_PMOS_MODEL" not in template_vars:
        template_vars["PDK_PMOS_MODEL"] = str(cfg.get("pmos_model", entry.get("pmos_model", "pch")))

    nmos_mismatch_text = pick_value("nmos_mismatch_file", "", None)
    pmos_mismatch_text = pick_value("pmos_mismatch_file", "", None)
    design_file_text = pick_value("design_file", "", None)
    invariant_text = pick_value("invariant_file", "", None)
    lod_text = pick_value("lod_file", "", None)
    if design_file_text:
        design_path = resolve_maybe_relative_path(design_file_text, config_base).resolve()
        template_vars["PDK_DESIGN_FILE"] = design_path.as_posix()
    if invariant_text:
        invariant_path = resolve_maybe_relative_path(invariant_text, config_base).resolve()
        template_vars["PDK_INVARIANT_FILE"] = invariant_path.as_posix()
    if lod_text:
        lod_path = resolve_maybe_relative_path(lod_text, config_base).resolve()
        template_vars["PDK_LOD_FILE"] = lod_path.as_posix()
    if nmos_mismatch_text:
        nmos_mismatch_path = resolve_maybe_relative_path(nmos_mismatch_text, config_base).resolve()
        template_vars["PDK_NMOS_MISMATCH_FILE"] = nmos_mismatch_path.as_posix()
    if pmos_mismatch_text:
        pmos_mismatch_path = resolve_maybe_relative_path(pmos_mismatch_text, config_base).resolve()
        template_vars["PDK_PMOS_MISMATCH_FILE"] = pmos_mismatch_path.as_posix()

    nmos_corner_pattern = pick_value("nmos_corner_pattern", "", None)
    pmos_corner_pattern = pick_value("pmos_corner_pattern", "", None)

    mismatch_cfg: dict[str, object] = {}
    if isinstance(entry.get("pdk_mismatch"), dict):
        mismatch_cfg.update(entry.get("pdk_mismatch", {}))
    if isinstance(cfg.get("pdk_mismatch"), dict):
        mismatch_cfg.update(cfg.get("pdk_mismatch", {}))

    def pick_mismatch_float(key: str, default: float) -> float:
        if key in mismatch_cfg and str(mismatch_cfg[key]).strip():
            return float(mismatch_cfg[key])
        return pick_float(f"pdk_mismatch_{key}", default)

    return PdkContext(
        pdk_id=requested_pdk_id,
        pdk_class=str(entry.get("pdk_class", "unknown")).strip().lower(),
        simulator=str(args.simulator),
        model_revision=pick_value("model_revision", "unspecified", None),
        license=pick_value("license", "unspecified", None),
        model_root=pick_value("model_root", "unspecified", None),
        macro_mode=pick_value("macro_mode", "6t-cell", None),
        registry_path=str(args.pdk_registry),
        config_path=str(args.pdk_config) if args.pdk_config is not None else "none",
        corner_map=corner_map,
        template_vars=template_vars,
        contract_metric_sources=contract_metric_sources,
        nmos_corner_pattern=nmos_corner_pattern,
        pmos_corner_pattern=pmos_corner_pattern,
        mismatch_sigma_w_rel=pick_mismatch_float("sigma_w_rel", DEFAULT_PDK_MISMATCH_SIGMA_W_REL),
        mismatch_sigma_l_rel=pick_mismatch_float("sigma_l_rel", DEFAULT_PDK_MISMATCH_SIGMA_L_REL),
        mismatch_clip_sigma=pick_mismatch_float("clip_sigma", DEFAULT_PDK_MISMATCH_CLIP_SIGMA),
    )


def build_operating_points(corners: Iterable[str], temps: Iterable[float], vdds: Iterable[float]) -> list[OperatingPoint]:
    points: list[OperatingPoint] = []
    for corner in corners:
        for temp_k in temps:
            for vdd in vdds:
                points.append(OperatingPoint(corner=corner, temp_k=float(temp_k), vdd=float(vdd)))
    return points


def load_spice_proxy_config(path: Path | None) -> dict[str, float]:
    config = dict(DEFAULT_SPICE_PROXY_CONFIG)
    if path is None:
        return config
    if not path.exists():
        raise FileNotFoundError(f"spice proxy config not found: {path}")

    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("spice proxy config must be a JSON object")

    for key in config:
        if key in loaded:
            config[key] = float(loaded[key])
    return config


def render_netlist(
    template_text: str,
    op: OperatingPoint,
    spice_proxy: dict[str, float],
    template_vars: dict[str, str] | None = None,
) -> str:
    text = (
        template_text
        .replace("__CORNER__", op.corner)
        .replace("__CORNER_GAIN__", f"{CORNER_GAIN[op.corner]:.6f}")
        .replace("__TEMP_K__", f"{op.temp_k:.6f}")
        .replace("__VDD__", f"{op.vdd:.6f}")
        .replace("__SNM_SCALE_MV__", f"{spice_proxy['snm_scale_mv']:.6f}")
        .replace("__NOISE_SCALE__", f"{spice_proxy['noise_scale']:.6f}")
        .replace("__NOISE_WRITE_WEIGHT__", f"{spice_proxy['noise_write_weight']:.6f}")
        .replace("__BER_CENTER_MV__", f"{spice_proxy['ber_center_mv']:.6f}")
        .replace("__BER_SLOPE_MV__", f"{spice_proxy['ber_slope_mv']:.6f}")
    )
    if template_vars:
        for key, value in template_vars.items():
            text = text.replace(f"__{key}__", str(value))
    for key, value in DEFAULT_MC_MISMATCH_TEMPLATE_VARS.items():
        text = text.replace(f"__{key}__", value)
    return text


def _render_xyce_measure_block(op: OperatingPoint, spice_proxy: dict[str, float]) -> str:
    vdd = float(op.vdd)
    snm_scale_mv = float(spice_proxy["snm_scale_mv"])
    noise_scale = float(spice_proxy["noise_scale"])
    noise_write_weight = float(spice_proxy["noise_write_weight"])
    ber_center_mv = float(spice_proxy["ber_center_mv"])
    ber_slope_mv = float(spice_proxy["ber_slope_mv"])
    return "\n".join(
        [
            "* Xyce-compatible measurement block (derived from ngspice control script)",
            ".measure tran VQ_HOLD find v(q) at=0.90n",
            ".measure tran VQ_READ find v(q) at=1.90n",
            ".measure tran VQ_W0 find v(q) at=2.90n",
            ".measure tran VQ_W1 find v(q) at=3.90n",
            ".measure tran SNM_PROXY MIN PARAM='abs(v(q)-v(qb))' from=1.00n to=2.00n",
            f".measure tran SNM_MV PARAM='SNM_PROXY * {snm_scale_mv:.12g}'",
            ".measure tran HOLD_SNM_MV PARAM='SNM_MV'",
            ".measure tran READ_DISTURB PARAM='abs(VQ_READ - VQ_HOLD)'",
            ".measure tran READ_SNM_MV PARAM='SNM_MV - (READ_DISTURB * 1000.0)'",
            f".measure tran WRITE_ERROR PARAM='abs(VQ_W1 - {vdd:.12g})'",
            f".measure tran WRITE_MARGIN_MV PARAM='({vdd:.12g} - WRITE_ERROR) * 1000.0'",
            f".measure tran NOISE_PROXY PARAM='{noise_scale:.12g} * (READ_DISTURB + {noise_write_weight:.12g} * WRITE_ERROR) / ({vdd:.12g} + 1e-9)'",
            ".measure tran NOISE_SIGMA PARAM='NOISE_PROXY'",
            ".measure tran READ_FAIL PARAM='1.0 / (1.0 + exp((READ_SNM_MV - 50.0) / 8.0))'",
            ".measure tran WRITE_FAIL PARAM='1.0 / (1.0 + exp((WRITE_MARGIN_MV - 50.0) / 8.0))'",
            f".measure tran BER_PROXY PARAM='1.0 / (1.0 + exp((SNM_MV - {ber_center_mv:.12g}) / {ber_slope_mv:.12g}))'",
            ".measure tran MEAS_SNM_MV PARAM='SNM_MV'",
            ".measure tran MEAS_NOISE PARAM='NOISE_PROXY'",
            ".measure tran MEAS_BER PARAM='BER_PROXY'",
            ".measure tran MEAS_HOLD_SNM_MV PARAM='HOLD_SNM_MV'",
            ".measure tran MEAS_READ_SNM_MV PARAM='READ_SNM_MV'",
            ".measure tran MEAS_WRITE_MARGIN_MV PARAM='WRITE_MARGIN_MV'",
            ".measure tran MEAS_NOISE_SIGMA PARAM='NOISE_SIGMA'",
            ".measure tran MEAS_READ_FAIL PARAM='READ_FAIL'",
            ".measure tran MEAS_WRITE_FAIL PARAM='WRITE_FAIL'",
        ]
    )


def adapt_external_netlist_for_simulator(
    netlist_text: str,
    *,
    simulator: str,
    op: OperatingPoint,
    spice_proxy: dict[str, float],
) -> str:
    sim = str(simulator).strip().lower()
    if sim != "xyce":
        return netlist_text

    stripped, _ = CONTROL_BLOCK_RE.subn("", netlist_text)
    measure_block = _render_xyce_measure_block(op, spice_proxy)
    end_pattern = re.compile(r"^\s*\.end\s*$", re.IGNORECASE | re.MULTILINE)
    if end_pattern.search(stripped):
        return end_pattern.sub(f"{measure_block}\n\n.end", stripped, count=1)
    return f"{stripped.rstrip()}\n\n{measure_block}\n\n.end\n"


def parse_spice_log(log_text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, pattern in REQUIRED_MEASURE_PATTERNS.items():
        match = pattern.search(log_text)
        if not match:
            raise RuntimeError(f"missing {key} in SPICE log")
        out[key] = float(match.group(1))

    for key, pattern in OPTIONAL_MEASURE_PATTERNS.items():
        match = pattern.search(log_text)
        if match:
            out[key] = float(match.group(1))

    if "hold_snm_mv" not in out:
        out["hold_snm_mv"] = float(out["snm_mv"])
    if "read_snm_mv" not in out:
        out["read_snm_mv"] = float(out["snm_mv"])
    if "write_margin_mv" not in out:
        out["write_margin_mv"] = float("nan")
    if "noise_sigma" not in out:
        out["noise_sigma"] = float(out["noise"])
    if "read_fail" not in out:
        out["read_fail"] = logistic_failure_from_margin(out["read_snm_mv"], center_mv=50.0, slope_mv=8.0)
    if "write_fail" not in out:
        out["write_fail"] = logistic_failure_from_margin(out["write_margin_mv"], center_mv=50.0, slope_mv=8.0)
    return out


def classify_spice_runtime_failure(err_text: str) -> tuple[str, str] | None:
    text = str(err_text or "")
    for pattern, code, recommendation in SPICE_RUNTIME_PATTERNS:
        if pattern.search(text):
            return code, recommendation
    return None


def clip_text_tail(text: str, max_lines: int = 30, max_chars: int = 3000) -> str:
    lines = [line for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    clipped = "\n".join(lines[-max_lines:])
    if len(clipped) <= max_chars:
        return clipped
    return clipped[-max_chars:]


def summarize_command_token(command_text: str | None) -> str:
    text = str(command_text or "").strip()
    if not text:
        return "n/a"
    return text.split()[0]


def resolve_ngspice_bin(explicit: str | None) -> str | None:
    if explicit:
        return explicit

    from_path = shutil.which("ngspice")
    if from_path:
        return from_path

    candidates = [
        Path(r"C:\msys64\ucrt64\bin\ngspice.exe"),
        Path(r"C:\msys64\mingw64\bin\ngspice.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _looks_like_existing_file_path(value: str) -> bool:
    token = str(value).strip()
    if not token:
        return False
    try:
        return Path(token).exists() and Path(token).is_file()
    except OSError:
        return False


def _prepare_spice_workspace(
    *,
    raw_dir: Path,
    case_name: str,
    template_vars: dict[str, str] | None,
) -> tuple[Path, dict[str, str] | None]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        return raw_dir, template_vars

    needs_local_copy = (" " in str(raw_dir.resolve()))
    if isinstance(template_vars, dict):
        needs_local_copy = needs_local_copy or any(
            (" " in str(value)) and _looks_like_existing_file_path(str(value))
            for value in template_vars.values()
        )
    if not needs_local_copy:
        return raw_dir, template_vars

    exec_root = Path(tempfile.gettempdir()) / "sram_spice_workspace" / case_name
    if exec_root.exists():
        shutil.rmtree(exec_root, ignore_errors=True)
    exec_root.mkdir(parents=True, exist_ok=True)

    localized_vars = dict(template_vars or {})
    asset_dir = exec_root / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    copied_dirs: dict[Path, Path] = {}
    for key, value in list(localized_vars.items()):
        token = str(value)
        if not _looks_like_existing_file_path(token):
            continue
        src_path = Path(token)
        src_dir = src_path.parent
        if src_dir not in copied_dirs:
            dst_dir = asset_dir / src_dir.name
            if dst_dir.exists():
                shutil.rmtree(dst_dir, ignore_errors=True)
            shutil.copytree(src_dir, dst_dir)
            copied_dirs[src_dir] = dst_dir
        dst_path = copied_dirs[src_dir] / src_path.name
        localized_vars[key] = dst_path.as_posix()

    return exec_root, localized_vars


def run_spice_ngspice(
    op: OperatingPoint,
    template_text: str,
    raw_dir: Path,
    ngspice_bin: str,
    spice_proxy: dict[str, float],
    template_vars: dict[str, str] | None = None,
    case_suffix: str = "",
) -> dict[str, float]:
    case_name = f"{op.case_id}{case_suffix}"
    exec_dir, exec_template_vars = _prepare_spice_workspace(
        raw_dir=raw_dir,
        case_name=case_name,
        template_vars=template_vars,
    )
    netlist_path = exec_dir / f"{case_name}.sp"
    log_path = exec_dir / f"{case_name}.log"
    requested_netlist_path = raw_dir / f"{case_name}.sp"
    requested_log_path = raw_dir / f"{case_name}.log"
    rendered = render_netlist(template_text, op, spice_proxy, exec_template_vars)
    netlist_path.write_text(rendered, encoding="utf-8")
    if netlist_path != requested_netlist_path:
        requested_netlist_path.write_text(rendered, encoding="utf-8")

    child_env = dict(os.environ)
    bin_dir = str(Path(ngspice_bin).resolve().parent)
    child_env["PATH"] = f"{bin_dir};{child_env.get('PATH', '')}"
    cmd = [ngspice_bin, "-b", "-o", str(log_path), str(netlist_path)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False, env=child_env)
    if completed.returncode != 0:
        err_text = completed.stderr.strip() or completed.stdout.strip()
        if not err_text and log_path.exists():
            log_tail = log_path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()[-25:]
            err_text = "\n".join(log_tail).strip()
        classification = classify_spice_runtime_failure(err_text)
        if classification is not None:
            code, recommendation = classification
            raise RuntimeError(
                f"[SPICE_RUNTIME:{code}] ngspice failed for {op.case_id}: {err_text}\n"
                f"Recommendation: {recommendation}\n"
                f"[SPICE_RUNTIME:{code}]"
            )
        raise RuntimeError(f"[SPICE_RUNTIME:GENERIC] ngspice failed for {op.case_id}: {err_text}")

    log_text = log_path.read_text(encoding="utf-8", errors="ignore")
    if log_path != requested_log_path:
        requested_log_path.write_text(log_text, encoding="utf-8")
    return parse_spice_log(log_text)


def render_external_sim_command(
    command_template: str,
    *,
    simulator: str,
    netlist_path: Path,
    log_path: Path,
    raw_dir: Path,
    case_id: str,
) -> str:
    return (
        str(command_template)
        .replace("__SIMULATOR__", str(simulator))
        .replace("__NETLIST__", str(netlist_path))
        .replace("__LOG_PATH__", str(log_path))
        .replace("__RAW_DIR__", str(raw_dir))
        .replace("__CASE_ID__", str(case_id))
    )


def classify_external_sim_failure(
    stderr_text: str,
    stdout_text: str,
    log_text: str,
    *,
    simulator: str,
) -> tuple[str, str] | None:
    merged = "\n".join([str(stderr_text or ""), str(stdout_text or ""), str(log_text or "")])
    sim = str(simulator or "").strip().lower()
    base = classify_spice_runtime_failure(merged)
    if base is not None:
        return base
    if re.search(r"not recognized as an internal or external command", merged, re.IGNORECASE):
        return (
            "EXTERNAL_SIM_BIN_NOT_FOUND",
            "External simulator command was not found. Install the tool or fix --external-sim-cmd.",
        )
    if re.search(r"(command not found|No such file or directory)", merged, re.IGNORECASE):
        return (
            "EXTERNAL_SIM_BIN_NOT_FOUND",
            "External simulator command was not found. Install the tool or fix --external-sim-cmd.",
        )
    if re.search(r"Subcircuit\s+\S+\s+has not been defined for instance", merged, re.IGNORECASE):
        if sim == "xyce":
            return (
                "XYCE_MODEL_CARD_INCOMPATIBLE",
                "Xyce could not resolve required subcircuit/model deck for this PDK. "
                "Use Spectre/HSPICE, or provide Xyce-native compatible model deck/netlist.",
            )
        return (
            "EXTERNAL_SIM_MODEL_UNRESOLVED",
            "Model/subcircuit could not be resolved by external simulator. Check include paths and model compatibility.",
        )
    if re.search(r"Model is required for device\s+\S+\s+and no valid model card found", merged, re.IGNORECASE):
        if sim == "xyce":
            return (
                "XYCE_MODEL_CARD_INCOMPATIBLE",
                "Xyce could not parse required model cards (for example PSP/BSIM-CMG decks). "
                "Use Spectre/HSPICE, or provide Xyce-native compatible model deck/netlist.",
            )
        return (
            "EXTERNAL_SIM_MODEL_UNRESOLVED",
            "Model cards were not accepted by external simulator. Check model syntax/support and include paths.",
        )
    return None


def run_spice_external(
    op: OperatingPoint,
    template_text: str,
    raw_dir: Path,
    simulator: str,
    external_sim_cmd: str,
    external_sim_timeout_sec: int,
    spice_proxy: dict[str, float],
    template_vars: dict[str, str] | None = None,
    case_suffix: str = "",
) -> dict[str, float]:
    case_name = f"{op.case_id}{case_suffix}"
    exec_dir, exec_template_vars = _prepare_spice_workspace(
        raw_dir=raw_dir,
        case_name=case_name,
        template_vars=template_vars,
    )
    netlist_path = exec_dir / f"{case_name}.sp"
    log_path = exec_dir / f"{case_name}.{simulator}.log"
    requested_netlist_path = raw_dir / f"{case_name}.sp"
    requested_log_path = raw_dir / f"{case_name}.{simulator}.log"
    rendered_netlist = render_netlist(template_text, op, spice_proxy, exec_template_vars)
    rendered_netlist = adapt_external_netlist_for_simulator(
        rendered_netlist,
        simulator=simulator,
        op=op,
        spice_proxy=spice_proxy,
    )
    netlist_path.write_text(rendered_netlist, encoding="utf-8")
    if netlist_path != requested_netlist_path:
        raw_dir.mkdir(parents=True, exist_ok=True)
        requested_netlist_path.write_text(rendered_netlist, encoding="utf-8")

    command_template = str(external_sim_cmd or "").strip()
    if not command_template:
        raise RuntimeError(
            f"[SPICE_RUNTIME:EXTERNAL_SIM_CMD_MISSING] simulator '{simulator}' selected for {op.case_id}, "
            "but no external command is configured. "
            "Recommendation: set --external-sim-cmd or pdk config key external_sim_cmd."
        )

    rendered_cmd = render_external_sim_command(
        command_template,
        simulator=simulator,
        netlist_path=netlist_path,
        log_path=log_path,
        raw_dir=exec_dir,
        case_id=case_name,
    )
    try:
        completed = subprocess.run(
            rendered_cmd,
            cwd=str(REPO_ROOT),
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(int(external_sim_timeout_sec), 1),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"[SPICE_RUNTIME:EXTERNAL_SIM_TIMEOUT] {simulator} timeout for {op.case_id}. "
            f"command='{summarize_command_token(command_template)}' timeout_sec={external_sim_timeout_sec}"
        ) from exc

    log_text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
    if log_text and log_path != requested_log_path:
        requested_log_path.write_text(log_text, encoding="utf-8")
    if completed.returncode != 0:
        failure = classify_external_sim_failure(
            completed.stderr,
            completed.stdout,
            log_text,
            simulator=simulator,
        )
        merged_tail = clip_text_tail("\n".join([completed.stderr or "", completed.stdout or "", log_text]))
        if failure is not None:
            code, recommendation = failure
            raise RuntimeError(
                f"[SPICE_RUNTIME:{code}] {simulator} failed for {op.case_id}: {merged_tail}\n"
                f"Recommendation: {recommendation}\n"
                f"[SPICE_RUNTIME:{code}]"
            )
        raise RuntimeError(
            f"[SPICE_RUNTIME:GENERIC] {simulator} failed for {op.case_id}: {merged_tail}"
        )

    merged_output = "\n".join(
        part for part in [log_text, completed.stdout or "", completed.stderr or ""] if str(part).strip()
    )
    try:
        return parse_spice_log(merged_output)
    except Exception as exc:
        raise RuntimeError(
            f"[SPICE_RUNTIME:EXTERNAL_SIM_PARSE_FAILED] unable to parse measure tags for {op.case_id} "
            f"from {simulator} output. command='{summarize_command_token(command_template)}'. "
            "Recommendation: ensure deck emits MEAS_* tags into log/stdout."
        ) from exc


def _sample_unit_scale(rng: random.Random, rel_sigma: float, clip_sigma: float) -> float:
    safe_sigma = max(float(rel_sigma), 0.0)
    if safe_sigma <= 0.0:
        return 1.0
    safe_clip = max(float(clip_sigma), 0.0)
    z = rng.gauss(0.0, 1.0)
    if safe_clip > 0.0:
        z = max(min(z, safe_clip), -safe_clip)
    sampled = 1.0 + (z * safe_sigma)
    return max(sampled, 0.1)


def sample_pdk_mismatch_template_vars(
    rng: random.Random,
    pdk_context: PdkContext | None,
) -> dict[str, str]:
    sigma_w_rel = (
        float(pdk_context.mismatch_sigma_w_rel)
        if pdk_context is not None
        else float(DEFAULT_PDK_MISMATCH_SIGMA_W_REL)
    )
    sigma_l_rel = (
        float(pdk_context.mismatch_sigma_l_rel)
        if pdk_context is not None
        else float(DEFAULT_PDK_MISMATCH_SIGMA_L_REL)
    )
    clip_sigma = (
        float(pdk_context.mismatch_clip_sigma)
        if pdk_context is not None
        else float(DEFAULT_PDK_MISMATCH_CLIP_SIGMA)
    )
    out: dict[str, str] = {}
    for device in MC_DEVICE_NAMES:
        out[f"MC_W_{device}"] = f"{_sample_unit_scale(rng, sigma_w_rel, clip_sigma):.8f}"
        l_scale = max(_sample_unit_scale(rng, sigma_l_rel, clip_sigma), 1.0)
        out[f"MC_L_{device}"] = f"{l_scale:.8f}"
    return out


def resolve_spice_mc_mode_effective(requested_mode: str, runs: int) -> str:
    mode = str(requested_mode).strip().lower()
    if max(int(runs), 1) <= 1 or mode == "off":
        return "off"
    if mode == "pdk_mismatch":
        return "pdk_mismatch"
    return "param_perturb"


def perturb_spice_proxy(base_proxy: dict[str, float], rng: random.Random) -> dict[str, float]:
    out = dict(base_proxy)
    rel_sigma = {
        "snm_scale_mv": 0.02,
        "noise_scale": 0.08,
        "noise_write_weight": 0.05,
        "ber_center_mv": 0.03,
        "ber_slope_mv": 0.06,
    }
    for key, sigma in rel_sigma.items():
        base_value = float(out[key])
        if key == "ber_center_mv":
            delta = rng.gauss(0.0, max(abs(base_value), 1.0) * sigma)
            out[key] = base_value + delta
            continue
        sampled = base_value * (1.0 + rng.gauss(0.0, sigma))
        if key == "noise_write_weight":
            sampled = max(0.0, min(sampled, 2.0))
        else:
            sampled = max(sampled, 1e-9)
        out[key] = sampled
    return out


def aggregate_spice_samples(samples: list[dict[str, float]]) -> dict[str, float]:
    if not samples:
        raise ValueError("no spice samples to aggregate")
    keys = (
        "snm_mv",
        "noise",
        "ber",
        "hold_snm_mv",
        "read_snm_mv",
        "write_margin_mv",
        "noise_sigma",
        "read_fail",
        "write_fail",
    )
    out: dict[str, float] = {}
    for key in keys:
        finite_values = [float(sample[key]) for sample in samples if math.isfinite(float(sample[key]))]
        out[key] = fmean(finite_values) if finite_values else float("nan")

    noise_values = [float(sample["noise"]) for sample in samples if math.isfinite(float(sample["noise"]))]
    if len(noise_values) >= 2:
        out["noise_sigma"] = float(pstdev(noise_values))
    return out


def run_spice_ngspice_with_mc(
    op: OperatingPoint,
    template_text: str,
    raw_dir: Path,
    ngspice_bin: str,
    spice_proxy: dict[str, float],
    template_vars: dict[str, str] | None,
    pdk_context: PdkContext | None,
    spice_mc_runs: int,
    mc_mode: str,
    mc_seed: int | None,
) -> dict[str, float]:
    runs = max(int(spice_mc_runs), 1)
    requested_mode = str(mc_mode).strip().lower()
    if runs == 1 or requested_mode == "off":
        return run_spice_ngspice(
            op=op,
            template_text=template_text,
            raw_dir=raw_dir,
            ngspice_bin=ngspice_bin,
            spice_proxy=spice_proxy,
            template_vars=template_vars,
        )

    effective_mode = requested_mode

    case_seed_base = int(mc_seed) if mc_seed is not None else 20260218
    samples: list[dict[str, float]] = []
    for idx in range(runs):
        sample_proxy = dict(spice_proxy)
        sample_template_vars = dict(template_vars or {})
        rng = random.Random(case_seed_base + idx)
        if effective_mode == "param_perturb":
            sample_proxy = perturb_spice_proxy(spice_proxy, rng)
        elif effective_mode == "pdk_mismatch":
            sample_template_vars.update(sample_pdk_mismatch_template_vars(rng, pdk_context))

        sample = run_spice_ngspice(
            op=op,
            template_text=template_text,
            raw_dir=raw_dir,
            ngspice_bin=ngspice_bin,
            spice_proxy=sample_proxy,
            template_vars=sample_template_vars,
            case_suffix=f"_mc{idx:03d}",
        )
        samples.append(sample)

    return aggregate_spice_samples(samples)


def run_spice_external_with_mc(
    op: OperatingPoint,
    template_text: str,
    raw_dir: Path,
    simulator: str,
    external_sim_cmd: str,
    external_sim_timeout_sec: int,
    spice_proxy: dict[str, float],
    template_vars: dict[str, str] | None,
    pdk_context: PdkContext | None,
    spice_mc_runs: int,
    mc_mode: str,
    mc_seed: int | None,
) -> dict[str, float]:
    runs = max(int(spice_mc_runs), 1)
    requested_mode = str(mc_mode).strip().lower()
    if runs == 1 or requested_mode == "off":
        return run_spice_external(
            op=op,
            template_text=template_text,
            raw_dir=raw_dir,
            simulator=simulator,
            external_sim_cmd=external_sim_cmd,
            external_sim_timeout_sec=external_sim_timeout_sec,
            spice_proxy=spice_proxy,
            template_vars=template_vars,
        )

    effective_mode = requested_mode
    case_seed_base = int(mc_seed) if mc_seed is not None else 20260218
    samples: list[dict[str, float]] = []
    for idx in range(runs):
        sample_proxy = dict(spice_proxy)
        sample_template_vars = dict(template_vars or {})
        rng = random.Random(case_seed_base + idx)
        if effective_mode == "param_perturb":
            sample_proxy = perturb_spice_proxy(spice_proxy, rng)
        elif effective_mode == "pdk_mismatch":
            sample_template_vars.update(sample_pdk_mismatch_template_vars(rng, pdk_context))

        sample = run_spice_external(
            op=op,
            template_text=template_text,
            raw_dir=raw_dir,
            simulator=simulator,
            external_sim_cmd=external_sim_cmd,
            external_sim_timeout_sec=external_sim_timeout_sec,
            spice_proxy=sample_proxy,
            template_vars=sample_template_vars,
            case_suffix=f"_mc{idx:03d}",
        )
        samples.append(sample)
    return aggregate_spice_samples(samples)


def run_spice_placeholder(op: OperatingPoint) -> dict[str, float]:
    temp_factor = (op.temp_k - 273.15) / 100.0
    volt_factor = 1.0 - op.vdd
    snm_mv = 200.0 * op.vdd * CORNER_GAIN[op.corner] * max(
        0.0,
        1.0 - ((op.temp_k - 300.0) / 300.0) * 0.25 - volt_factor * 0.5,
    )
    noise = 0.05 * (1.0 + 0.5 * temp_factor) * (1.0 + 0.3 * volt_factor)
    ber = logistic_ber_from_snm(
        snm_mv=snm_mv,
        center_mv=float(DEFAULT_SPICE_PROXY_CONFIG["ber_center_mv"]),
        slope_mv=float(DEFAULT_SPICE_PROXY_CONFIG["ber_slope_mv"]),
    )
    noise = max(noise, 0.0)
    hold_snm_mv = snm_mv
    read_snm_mv = snm_mv - noise * 120.0
    write_margin_mv = (op.vdd - noise) * 1000.0
    read_fail = 1.0 / (1.0 + math.exp((read_snm_mv - 50.0) / 8.0))
    write_fail = 1.0 / (1.0 + math.exp((write_margin_mv - 50.0) / 8.0))
    return {
        "snm_mv": snm_mv,
        "noise": noise,
        "ber": ber,
        "hold_snm_mv": hold_snm_mv,
        "read_snm_mv": read_snm_mv,
        "write_margin_mv": write_margin_mv,
        "noise_sigma": noise,
        "read_fail": read_fail,
        "write_fail": write_fail,
    }


def evaluate_operating_point(
    *,
    op_index: int,
    op: OperatingPoint,
    args: argparse.Namespace,
    pdk_context: PdkContext | None,
    spice_proxy: dict[str, float],
    template_text: str,
    ngspice_bin: str | None,
) -> dict[str, float | str | bool]:
    pdk_template_vars: dict[str, str] | None = None
    if pdk_context is not None:
        pdk_template_vars = dict(pdk_context.template_vars)
        mapped_corner = pdk_context.corner_map.get(op.corner, op.corner)
        pdk_template_vars["PDK_CORNER"] = mapped_corner

        if pdk_context.nmos_corner_pattern:
            nmos_corner_text = pdk_context.nmos_corner_pattern.replace("{corner}", mapped_corner)
            nmos_corner_path = resolve_maybe_relative_path(nmos_corner_text, REPO_ROOT)
            pdk_template_vars["PDK_NMOS_CORNER_FILE"] = nmos_corner_path.as_posix()
        if pdk_context.pmos_corner_pattern:
            pmos_corner_text = pdk_context.pmos_corner_pattern.replace("{corner}", mapped_corner)
            pmos_corner_path = resolve_maybe_relative_path(pmos_corner_text, REPO_ROOT)
            pdk_template_vars["PDK_PMOS_CORNER_FILE"] = pmos_corner_path.as_posix()

    if args.spice_source in {"ngspice", "pdk"}:
        case_mc_seed = None if args.spice_seed is None else int(args.spice_seed) + (op_index * 1000)
        spice_start = time.perf_counter()
        if args.simulator == "ngspice":
            if not ngspice_bin:
                raise RuntimeError("ngspice bin is required for ngspice simulator mode")
            spice = run_spice_ngspice_with_mc(
                op=op,
                template_text=template_text,
                raw_dir=args.raw_dir,
                ngspice_bin=ngspice_bin,
                spice_proxy=spice_proxy,
                template_vars=pdk_template_vars,
                pdk_context=pdk_context,
                spice_mc_runs=args.spice_mc_runs,
                mc_mode=args.mc_mode,
                mc_seed=case_mc_seed,
            )
        else:
            spice = run_spice_external_with_mc(
                op=op,
                template_text=template_text,
                raw_dir=args.raw_dir,
                simulator=str(args.simulator),
                external_sim_cmd=str(args.external_sim_cmd or ""),
                external_sim_timeout_sec=int(args.external_sim_timeout_sec),
                spice_proxy=spice_proxy,
                template_vars=pdk_template_vars,
                pdk_context=pdk_context,
                spice_mc_runs=args.spice_mc_runs,
                mc_mode=args.mc_mode,
                mc_seed=case_mc_seed,
            )
        spice_runtime_ms = (time.perf_counter() - spice_start) * 1000.0
    else:
        spice_start = time.perf_counter()
        spice = run_spice_placeholder(op)
        spice_runtime_ms = (time.perf_counter() - spice_start) * 1000.0

    native_start = time.perf_counter()
    native = run_native(
        op=op,
        backend=args.backend,
        num_cells=args.num_cells,
        monte_carlo_runs=args.monte_carlo_runs,
        noise_enable=args.native_noise_enable,
        variability_enable=args.native_variability_enable,
        thermal_enable=args.native_thermal_enable,
        seed=args.native_seed,
    )
    native_runtime_ms = (time.perf_counter() - native_start) * 1000.0
    if native["fallback"]:
        raise RuntimeError(
            f"native execution fallback detected at {op.case_id}; "
            "strict native requirement violated."
        )

    spice_mc_mode_effective = resolve_spice_mc_mode_effective(str(args.mc_mode), int(args.spice_mc_runs))

    return {
        "case_id": op.case_id,
        "corner": op.corner,
        "temp_k": op.temp_k,
        "vdd": op.vdd,
        "spice_snm_mv": spice["snm_mv"],
        "native_snm_mv": native["snm_mv"],
        "delta_snm_mv": float(native["snm_mv"]) - float(spice["snm_mv"]),
        "spice_noise": spice["noise"],
        "native_noise": native["noise"],
        "delta_noise": float(native["noise"]) - float(spice["noise"]),
        "spice_ber_raw": spice["ber"],
        "native_ber_raw": native["ber_raw"],
        "spice_ber": spice["ber"],
        "native_ber": native["ber_raw"],
        "delta_ber": float(native["ber_raw"]) - float(spice["ber"]),
        "spice_hold_snm_mv": spice["hold_snm_mv"],
        "native_hold_snm_mv": native["hold_snm_mv"],
        "delta_hold_snm_mv": float(native["hold_snm_mv"]) - float(spice["hold_snm_mv"]),
        "spice_read_snm_mv": spice["read_snm_mv"],
        "native_read_snm_mv": native["read_snm_mv"],
        "delta_read_snm_mv": float(native["read_snm_mv"]) - float(spice["read_snm_mv"]),
        "spice_write_margin_mv": spice["write_margin_mv"],
        "native_write_margin_mv": native["write_margin_mv"],
        "delta_write_margin_mv": float(native["write_margin_mv"]) - float(spice["write_margin_mv"]),
        "spice_noise_sigma": spice["noise_sigma"],
        "native_noise_sigma": native["noise_sigma"],
        "delta_noise_sigma": float(native["noise_sigma"]) - float(spice["noise_sigma"]),
        "spice_read_fail": spice["read_fail"],
        "spice_read_fail_raw": spice["read_fail"],
        "native_read_fail": native["read_fail"],
        "delta_read_fail": float(native["read_fail"]) - float(spice["read_fail"]),
        "spice_write_fail": spice["write_fail"],
        "spice_write_fail_raw": spice["write_fail"],
        "native_write_fail": native["write_fail"],
        "delta_write_fail": float(native["write_fail"]) - float(spice["write_fail"]),
        "native_backend_label": native["backend"],
        "native_engine": native["engine"],
        "data_source": args.data_source,
        "spice_source": args.spice_source,
        "simulator": args.simulator,
        "spice_runtime_ms": float(spice_runtime_ms),
        "native_runtime_ms": float(native_runtime_ms),
        "spice_mc_runs": int(args.spice_mc_runs),
        "spice_mc_mode": str(args.mc_mode),
        "spice_mc_mode_effective": spice_mc_mode_effective,
        "spice_mc_seed": int(args.spice_seed) if args.spice_seed is not None else "",
        "measure_contract_revision": MEASURE_CONTRACT_REVISION,
        "pdk_id": pdk_context.pdk_id if pdk_context else "",
        "pdk_class": pdk_context.pdk_class if pdk_context else "",
        "model_revision": pdk_context.model_revision if pdk_context else "",
        "macro_mode": pdk_context.macro_mode if pdk_context else "",
        "pdk_license": pdk_context.license if pdk_context else "",
        "ber_contract_mode": args.ber_contract_mode,
        "snm_noise_contract_mode": args.snm_noise_contract_mode,
    }


def run_native(
    op: OperatingPoint,
    backend: str,
    num_cells: int,
    monte_carlo_runs: int,
    noise_enable: bool,
    variability_enable: bool,
    thermal_enable: bool,
    seed: int | None,
) -> dict[str, float | str | bool]:
    input_data = [i % 2 for i in range(max(num_cells, 1))]
    request = {
        "backend": backend,
        "temperature": op.temp_k,
        "voltage": op.vdd,
        "num_cells": max(num_cells, 1),
        "input_data": input_data,
        "noise_enable": bool(noise_enable),
        "variability_enable": bool(variability_enable),
        "monte_carlo_runs": max(monte_carlo_runs, 1),
        "width": 1.0,
        "length": 1.0,
        "include_thermal_noise": bool(thermal_enable),
        "require_native": True,
        "prefer_hybrid_gate_logic": False,
    }
    if seed is not None:
        request["seed"] = int(seed)
    result = simulate_array(request)
    exec_meta = result.get("_exec", {}) if isinstance(result, dict) else {}
    noise_values = [float(v) for v in result.get("noise_values", [])]
    snm_values = [float(v) for v in result.get("snm_values", [])]
    snm_mv = (fmean(snm_values) * 1000.0) if snm_values else 0.0
    noise = fmean(noise_values) if noise_values else 0.0
    ber_raw = safe_float(result.get("bit_error_rate", 0.0), default=0.0)
    read_snm_mv = snm_mv - (noise * 120.0)
    write_margin_mv_raw = safe_float(result.get("write_margin_mv", float("nan")), default=float("nan"))
    write_margin_mv = (
        write_margin_mv_raw
        if math.isfinite(write_margin_mv_raw)
        else max((float(op.vdd) - noise), 0.0) * 1000.0
    )
    read_fail = logistic_failure_from_margin(read_snm_mv, center_mv=50.0, slope_mv=8.0)
    write_fail = logistic_failure_from_margin(write_margin_mv, center_mv=50.0, slope_mv=8.0)

    return {
        "backend": str(result.get("backend", "unknown")),
        "engine": str(exec_meta.get("selected", "unknown")),
        "fallback": bool(exec_meta.get("fallback", True)),
        "snm_mv": snm_mv,
        "noise": noise,
        "ber": ber_raw,
        "ber_raw": ber_raw,
        "hold_snm_mv": snm_mv,
        "read_snm_mv": read_snm_mv,
        "write_margin_mv": write_margin_mv,
        "noise_sigma": noise,
        "read_fail": read_fail,
        "write_fail": write_fail,
    }


def write_csv(path: Path, rows: list[dict[str, float | str | bool]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def mean_abs(rows: list[dict[str, float | str | bool]], key: str) -> float:
    values = [abs(float(row[key])) for row in rows]
    return fmean(values) if values else 0.0


def mean_abs_finite(rows: list[dict[str, float | str | bool]], key: str) -> float:
    values: list[float] = []
    for row in rows:
        value = float(row[key])
        if math.isfinite(value):
            values.append(abs(value))
    if not values:
        return float("nan")
    return fmean(values)


def mean_abs_log10_diff(
    rows: list[dict[str, float | str | bool]],
    left_key: str,
    right_key: str,
    floor: float = 1e-18,
) -> float:
    safe_floor = max(float(floor), 1e-30)
    values = []
    for row in rows:
        left = max(float(row[left_key]), safe_floor)
        right = max(float(row[right_key]), safe_floor)
        values.append(abs(math.log10(left) - math.log10(right)))
    return fmean(values) if values else 0.0


def fmt_metric(value: float) -> str:
    if math.isfinite(value):
        return f"{value:.6f}"
    return "n/a"


def write_report(
    path: Path,
    rows: list[dict[str, float | str | bool]],
    args: argparse.Namespace,
    spice_source: str,
    csv_path: Path,
    spice_proxy: dict[str, float],
    pdk_context: PdkContext | None,
    snm_noise_contract_summary: dict[str, object],
) -> None:
    mae_snm_mv = mean_abs(rows, "delta_snm_mv")
    mae_noise = mean_abs(rows, "delta_noise")
    mae_ber = mean_abs(rows, "delta_ber")
    mae_hold_snm_mv = mean_abs_finite(rows, "delta_hold_snm_mv")
    mae_read_snm_mv = mean_abs_finite(rows, "delta_read_snm_mv")
    mae_write_margin_mv = mean_abs_finite(rows, "delta_write_margin_mv")
    mae_noise_sigma = mean_abs_finite(rows, "delta_noise_sigma")
    mae_read_fail = mean_abs_finite(rows, "delta_read_fail")
    mae_write_fail = mean_abs_finite(rows, "delta_write_fail")
    raw_snm_values = [
        abs(float(row["native_snm_mv"]) - float(row.get("spice_snm_mv_raw", row["spice_snm_mv"])))
        for row in rows
    ]
    mae_snm_mv_raw = fmean(raw_snm_values) if raw_snm_values else float("nan")
    raw_noise_sigma_values = [
        abs(float(row["native_noise_sigma"]) - float(row.get("spice_noise_sigma_raw", row["spice_noise_sigma"])))
        for row in rows
    ]
    mae_noise_sigma_raw = fmean(raw_noise_sigma_values) if raw_noise_sigma_values else float("nan")
    raw_read_fail_values = [
        abs(float(row["native_read_fail"]) - float(row.get("spice_read_fail_raw", row.get("spice_read_fail", float("nan")))))
        for row in rows
        if math.isfinite(float(row["native_read_fail"])) and math.isfinite(float(row.get("spice_read_fail_raw", row.get("spice_read_fail", float("nan")))))
    ]
    mae_read_fail_raw = fmean(raw_read_fail_values) if raw_read_fail_values else float("nan")
    raw_write_fail_values = [
        abs(float(row["native_write_fail"]) - float(row.get("spice_write_fail_raw", row.get("spice_write_fail", float("nan")))))
        for row in rows
        if math.isfinite(float(row["native_write_fail"])) and math.isfinite(float(row.get("spice_write_fail_raw", row.get("spice_write_fail", float("nan")))))
    ]
    mae_write_fail_raw = fmean(raw_write_fail_values) if raw_write_fail_values else float("nan")
    mae_log10_ber = mean_abs_log10_diff(rows, "native_ber", "spice_ber")
    max_abs_ber = max(abs(float(row["delta_ber"])) for row in rows) if rows else 0.0
    raw_ber_values = [abs(float(row["native_ber_raw"]) - float(row["spice_ber_raw"])) for row in rows]
    mae_ber_raw = fmean(raw_ber_values) if raw_ber_values else float("nan")
    mae_log10_ber_raw = mean_abs_log10_diff(rows, "native_ber_raw", "spice_ber_raw")
    max_abs_ber_raw = max(abs(float(row["native_ber_raw"]) - float(row["spice_ber_raw"])) for row in rows) if rows else 0.0
    mae_ber_contract = mean_abs_finite(rows, "delta_ber_contract")
    mae_log10_ber_contract = mean_abs_log10_diff(rows, "native_ber_contract", "spice_ber_contract")
    max_abs_ber_contract = (
        max(abs(float(row["native_ber_contract"]) - float(row["spice_ber_contract"])) for row in rows) if rows else 0.0
    )
    ber_contract_center_mv = safe_float(rows[0].get("ber_contract_center_mv"), default=float("nan")) if rows else float("nan")
    ber_contract_slope_mv = safe_float(rows[0].get("ber_contract_slope_mv"), default=float("nan")) if rows else float("nan")
    ber_contract_fit_samples = int(safe_float(rows[0].get("ber_contract_fit_samples"), default=0.0)) if rows else 0
    spice_mc_mode_effective = resolve_spice_mc_mode_effective(str(args.mc_mode), int(args.spice_mc_runs))
    spice_runtime_values = [
        safe_float(row.get("spice_runtime_ms"), default=float("nan"))
        for row in rows
        if math.isfinite(safe_float(row.get("spice_runtime_ms"), default=float("nan")))
    ]
    native_runtime_values = [
        safe_float(row.get("native_runtime_ms"), default=float("nan"))
        for row in rows
        if math.isfinite(safe_float(row.get("native_runtime_ms"), default=float("nan")))
    ]
    mean_spice_runtime_ms = fmean(spice_runtime_values) if spice_runtime_values else float("nan")
    mean_native_runtime_ms = fmean(native_runtime_values) if native_runtime_values else float("nan")
    spice_runtime_per_mc_ms = (
        mean_spice_runtime_ms / max(int(args.spice_mc_runs), 1)
        if math.isfinite(mean_spice_runtime_ms)
        else float("nan")
    )

    lines = [
        "# SPICE Correlation Report",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Data source: `{args.data_source}`",
        f"- SPICE source: `{spice_source}`",
        f"- Simulator: `{args.simulator}`",
        f"- External sim command token: `{summarize_command_token(args.external_sim_cmd)}`",
        f"- External sim timeout (sec): `{args.external_sim_timeout_sec}`",
        f"- PDK ID: `{pdk_context.pdk_id if pdk_context else 'n/a'}`",
        f"- PDK class: `{pdk_context.pdk_class if pdk_context else 'n/a'}`",
        f"- Model revision: `{pdk_context.model_revision if pdk_context else 'n/a'}`",
        f"- Macro mode: `{pdk_context.macro_mode if pdk_context else 'n/a'}`",
        f"- PDK license: `{pdk_context.license if pdk_context else 'n/a'}`",
        f"- Model root: `{pdk_context.model_root if pdk_context else 'n/a'}`",
        f"- PDK registry: `{pdk_context.registry_path if pdk_context else 'n/a'}`",
        f"- PDK config: `{pdk_context.config_path if pdk_context else 'n/a'}`",
        f"- Native backend: `{args.backend}`",
        f"- Measure contract revision: `{MEASURE_CONTRACT_REVISION}`",
        f"- PVT grid: corners=`{args.corners}` temps_k=`{args.temps_k}` vdds=`{args.vdds}`",
        f"- Operating points: `{len(rows)}`",
        f"- Raw CSV: `{csv_path.as_posix()}`",
        f"- Native flags: noise=`{args.native_noise_enable}` variability=`{args.native_variability_enable}` thermal=`{args.native_thermal_enable}` seed=`{args.native_seed}`",
        f"- SPICE MC: mode=`{args.mc_mode}` runs=`{args.spice_mc_runs}` seed=`{args.spice_seed}`",
        f"- SPICE MC effective mode: `{spice_mc_mode_effective}`",
        f"- Mean SPICE runtime per operating point (ms): `{fmt_metric(mean_spice_runtime_ms)}`",
        f"- Mean SPICE runtime per MC sample (ms): `{fmt_metric(spice_runtime_per_mc_ms)}`",
        f"- Mean Native runtime per operating point (ms): `{fmt_metric(mean_native_runtime_ms)}`",
        f"- SNM/Noise contract mode: `{args.snm_noise_contract_mode}`",
        f"- Allow contract fallback: `{bool(args.allow_contract_fallback)}`",
        f"- BER contract mode: `{args.ber_contract_mode}`",
        f"- BER contract params (center/slope mV): `{fmt_metric(ber_contract_center_mv)} / {fmt_metric(ber_contract_slope_mv)}` (fit samples `{ber_contract_fit_samples}`)",
        f"- Proxy config: `{args.spice_proxy_config}`",
        "",
        "## Error Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| MAE(SNM mV) | {fmt_metric(mae_snm_mv)} |",
        f"| MAE(SNM mV raw-native) | {fmt_metric(mae_snm_mv_raw)} |",
        f"| MAE(noise) | {fmt_metric(mae_noise)} |",
        f"| MAE(BER) | {fmt_metric(mae_ber)} |",
        f"| MAE(log10 BER) | {fmt_metric(mae_log10_ber)} |",
        f"| Max |delta BER| | {fmt_metric(max_abs_ber)} |",
        f"| MAE(BER raw-native) | {fmt_metric(mae_ber_raw)} |",
        f"| MAE(log10 BER raw-native) | {fmt_metric(mae_log10_ber_raw)} |",
        f"| Max |delta BER| raw-native | {fmt_metric(max_abs_ber_raw)} |",
        f"| MAE(BER contract) | {fmt_metric(mae_ber_contract)} |",
        f"| MAE(log10 BER contract) | {fmt_metric(mae_log10_ber_contract)} |",
        f"| Max |delta BER| contract | {fmt_metric(max_abs_ber_contract)} |",
        f"| MAE(Hold SNM mV) | {fmt_metric(mae_hold_snm_mv)} |",
        f"| MAE(Read SNM mV) | {fmt_metric(mae_read_snm_mv)} |",
        f"| MAE(Write Margin mV) | {fmt_metric(mae_write_margin_mv)} |",
        f"| MAE(Noise Sigma) | {fmt_metric(mae_noise_sigma)} |",
        f"| MAE(Noise Sigma raw-native) | {fmt_metric(mae_noise_sigma_raw)} |",
        f"| MAE(Read Fail) | {fmt_metric(mae_read_fail)} |",
        f"| MAE(Read Fail raw-native) | {fmt_metric(mae_read_fail_raw)} |",
        f"| MAE(Write Fail) | {fmt_metric(mae_write_fail)} |",
        f"| MAE(Write Fail raw-native) | {fmt_metric(mae_write_fail_raw)} |",
        "",
        "## SPICE Proxy Parameters",
        "",
        "| Key | Value |",
        "|---|---:|",
        f"| snm_scale_mv | {spice_proxy['snm_scale_mv']:.6f} |",
        f"| noise_scale | {spice_proxy['noise_scale']:.6f} |",
        f"| noise_write_weight | {spice_proxy['noise_write_weight']:.6f} |",
        f"| ber_center_mv | {spice_proxy['ber_center_mv']:.6f} |",
        f"| ber_slope_mv | {spice_proxy['ber_slope_mv']:.6f} |",
        "",
        "## Contract Fit Summary",
        "",
        "| Metric | Requested Raw Source | Chosen Raw Source | Span | Finite | Fallback | Invalid Raw | Reason | Fit Status | Group Fallbacks | Groups | Global a | Global b | Samples |",
        "|---|---|---|---:|---:|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    metrics_summary = snm_noise_contract_summary.get("metrics", {}) if isinstance(snm_noise_contract_summary, dict) else {}
    for metric_name in (
        "snm_mv",
        "hold_snm_mv",
        "read_snm_mv",
        "write_margin_mv",
        "noise",
        "noise_sigma",
    ):
        item = metrics_summary.get(metric_name, {}) if isinstance(metrics_summary, dict) else {}
        lines.append(
            f"| {metric_name} | {str(item.get('requested_raw_key', '')) or 'n/a'} | "
            f"{str(item.get('source_raw_key', 'n/a'))} | "
            f"{fmt_metric(safe_float(item.get('source_raw_span'), float('nan')))} | "
            f"{int(safe_float(item.get('source_finite_count'), 0.0))} | "
            f"{'yes' if bool(item.get('fallback_used', False)) else 'no'} | "
            f"{'yes' if bool(item.get('invalid_raw_metric', False)) else 'no'} | "
            f"{str(item.get('reason', 'n/a'))} | "
            f"{str(item.get('fit_status', 'n/a'))} | "
            f"{int(safe_float(item.get('group_fit_fallbacks'), 0.0))} | "
            f"{int(safe_float(item.get('group_count'), 0.0))} | "
            f"{fmt_metric(safe_float(item.get('global_a'), float('nan')))} | "
            f"{fmt_metric(safe_float(item.get('global_b'), float('nan')))} | "
            f"{int(safe_float(item.get('global_samples'), 0.0))} |"
        )
    lines.extend(
        [
            "",
        "## Notes",
        "",
        "- The bundled template uses simplified compact models; replace with PDK-calibrated models for signoff.",
        "- v2 metrics are proxy-compatible unless the template emits physically extracted metrics.",
        "- Keep this report in version control with the exact command line used.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SPICE vs native correlation sweep")
    parser.add_argument("--spice-source", choices=list(SPICE_SOURCE_CHOICES), default="ngspice")
    parser.add_argument(
        "--simulator",
        choices=list(SIMULATOR_CHOICES),
        default="auto",
        help="simulation backend selector (pdk mode supports ngspice and external adapter scaffolding)",
    )
    parser.add_argument("--pdk-id", default=None, help="PDK identifier from pdk_registry.json")
    parser.add_argument(
        "--pdk-registry",
        type=Path,
        default=DEFAULT_PDK_REGISTRY_PATH,
        help="PDK registry JSON path",
    )
    parser.add_argument(
        "--pdk-config",
        type=Path,
        default=None,
        help="PDK-specific run config JSON (optional)",
    )
    parser.add_argument("--backend", choices=["standard", "hybrid"], default="hybrid")
    parser.add_argument("--corners", default=None)
    parser.add_argument("--temps-k", default=None)
    parser.add_argument("--vdds", default=None)
    parser.add_argument("--num-cells", type=int, default=256)
    parser.add_argument("--monte-carlo-runs", type=int, default=200)
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="number of operating points to process concurrently (default: 1)",
    )
    parser.add_argument("--spice-mc-runs", type=int, default=1)
    parser.add_argument("--spice-seed", type=int, default=20260218)
    parser.add_argument(
        "--mc-mode",
        choices=list(MC_MODE_CHOICES),
        default="off",
        help="SPICE-side MC mode: off|param_perturb|pdk_mismatch",
    )
    parser.add_argument(
        "--ber-contract-mode",
        choices=list(BER_CONTRACT_MODE_CHOICES),
        default="native_fit",
        help="BER alignment mode: raw_native|fixed_proxy|native_fit",
    )
    parser.add_argument(
        "--snm-noise-contract-mode",
        choices=list(SNM_NOISE_CONTRACT_MODE_CHOICES),
        default="affine_corner_temp",
        help="SNM/noise alignment mode: raw_native|affine_global|affine_corner|affine_corner_temp",
    )
    parser.add_argument(
        "--allow-contract-fallback",
        action="store_true",
        help="allow fallback to alternate raw contract source when explicit/primary source is invalid",
    )
    parser.add_argument("--native-noise-enable", default="true", help="true|false")
    parser.add_argument("--native-variability-enable", default="true", help="true|false")
    parser.add_argument("--native-thermal-enable", default="true", help="true|false")
    parser.add_argument("--native-seed", type=int, default=None)
    parser.add_argument(
        "--data-source",
        choices=list(DATA_SOURCE_CHOICES),
        default=None,
        help="report data provenance label (auto-selected in pdk mode if omitted)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--spice-proxy-config",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--ngspice-bin",
        default=None,
        help="explicit ngspice executable path (optional)",
    )
    parser.add_argument(
        "--external-sim-cmd",
        default=None,
        help=(
            "external simulator command template for spectre|hspice|xyce. "
            "Placeholders: __SIMULATOR__ __NETLIST__ __LOG_PATH__ __RAW_DIR__ __CASE_ID__"
        ),
    )
    parser.add_argument(
        "--external-sim-timeout-sec",
        type=int,
        default=None,
        help="timeout for external simulator adapter path (default: 900)",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "results" / "raw",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "results" / "spice_vs_native.csv",
    )
    parser.add_argument(
        "--out-report",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "reports" / "spice_correlation_report.md",
    )
    args = parser.parse_args()

    pdk_context = load_pdk_context(args)
    if pdk_context is None:
        if args.corners is None:
            args.corners = DEFAULT_CORNERS_TEXT
        if args.temps_k is None:
            args.temps_k = DEFAULT_TEMPS_K_TEXT
        if args.vdds is None:
            args.vdds = DEFAULT_VDDS_TEXT
        if args.data_source is None:
            args.data_source = "proxy-calibrated"
        args.data_source = normalize_data_source(args.data_source)

        if args.template is None:
            args.template = DEFAULT_TEMPLATE_PATH
        else:
            args.template = args.template.resolve()

        if args.spice_proxy_config is None:
            args.spice_proxy_config = DEFAULT_SPICE_PROXY_CONFIG_PATH
        else:
            args.spice_proxy_config = args.spice_proxy_config.resolve()

        if args.simulator == "auto":
            if args.spice_source == "placeholder":
                args.simulator = "placeholder"
            else:
                args.simulator = "ngspice"
        elif args.spice_source == "ngspice" and args.simulator != "ngspice":
            raise ValueError("--simulator must be ngspice (or auto) when --spice-source ngspice")
        elif args.spice_source == "placeholder" and args.simulator not in {"placeholder", "ngspice"}:
            raise ValueError("--simulator must be placeholder|ngspice|auto when --spice-source placeholder")

    if args.data_source is None:
        args.data_source = "proxy-calibrated"
    args.data_source = normalize_data_source(args.data_source)
    if args.external_sim_timeout_sec is None:
        args.external_sim_timeout_sec = DEFAULT_EXTERNAL_SIM_TIMEOUT_SEC
    args.external_sim_timeout_sec = max(int(args.external_sim_timeout_sec), 1)

    corners = parse_corner_list(args.corners)
    temps_k = parse_float_list(args.temps_k)
    vdds = parse_float_list(args.vdds)
    args.native_noise_enable = parse_bool_arg(args.native_noise_enable)
    args.native_variability_enable = parse_bool_arg(args.native_variability_enable)
    args.native_thermal_enable = parse_bool_arg(args.native_thermal_enable)
    args.spice_mc_runs = max(int(args.spice_mc_runs), 1)

    spice_proxy = load_spice_proxy_config(args.spice_proxy_config)
    points = build_operating_points(corners, temps_k, vdds)

    ngspice_bin = None
    template_text = ""
    if args.spice_source in {"ngspice", "pdk"}:
        if args.simulator == "ngspice":
            ngspice_bin = resolve_ngspice_bin(args.ngspice_bin)
            if not ngspice_bin:
                raise RuntimeError(
                    "ngspice executable not found. Install ngspice or run with "
                    "--spice-source placeholder for dry-run pipeline testing."
                )
        elif args.simulator not in EXTERNAL_SIMULATOR_CHOICES:
            raise RuntimeError(
                f"unsupported simulator '{args.simulator}' for spice-source '{args.spice_source}' "
                f"(supported: ngspice,{','.join(EXTERNAL_SIMULATOR_CHOICES)})"
            )
        template_text = args.template.read_text(encoding="utf-8")
        args.raw_dir.mkdir(parents=True, exist_ok=True)

    args.max_workers = max(int(args.max_workers), 1)
    rows: list[dict[str, float | str | bool]] = []
    if args.max_workers == 1:
        for op_index, op in enumerate(points):
            row = evaluate_operating_point(
                op_index=op_index,
                op=op,
                args=args,
                pdk_context=pdk_context,
                spice_proxy=spice_proxy,
                template_text=template_text,
                ngspice_bin=ngspice_bin,
            )
            rows.append(row)
    else:
        ordered_rows: list[dict[str, float | str | bool] | None] = [None] * len(points)
        with cf.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_index: dict[cf.Future[dict[str, float | str | bool]], int] = {}
            for op_index, op in enumerate(points):
                future = executor.submit(
                    evaluate_operating_point,
                    op_index=op_index,
                    op=op,
                    args=args,
                    pdk_context=pdk_context,
                    spice_proxy=spice_proxy,
                    template_text=template_text,
                    ngspice_bin=ngspice_bin,
                )
                future_to_index[future] = op_index

            for future in cf.as_completed(future_to_index):
                op_index = future_to_index[future]
                op = points[op_index]
                try:
                    ordered_rows[op_index] = future.result()
                except Exception as exc:
                    raise RuntimeError(f"operating point failed at {op.case_id}: {exc}") from exc

        rows = [row for row in ordered_rows if row is not None]

    snm_noise_contract_summary = apply_snm_noise_contract(
        rows=rows,
        contract_mode=args.snm_noise_contract_mode,
        metric_source_overrides=pdk_context.contract_metric_sources if pdk_context is not None else None,
        allow_fallback=bool(args.allow_contract_fallback),
    )

    default_center_mv = float(spice_proxy["ber_center_mv"])
    default_slope_mv = float(spice_proxy["ber_slope_mv"])
    if args.ber_contract_mode == "native_fit":
        ber_contract_center_mv, ber_contract_slope_mv, ber_fit_samples = fit_native_ber_contract_params(
            rows=rows,
            default_center_mv=default_center_mv,
            default_slope_mv=default_slope_mv,
        )
    else:
        ber_contract_center_mv = default_center_mv
        ber_contract_slope_mv = default_slope_mv
        ber_fit_samples = len(rows)

    for row in rows:
        spice_snm_mv = safe_float(row.get("spice_snm_mv"))
        native_snm_mv = safe_float(row.get("native_snm_mv"))
        spice_ber_raw = safe_float(row.get("spice_ber_raw"), default=0.0)
        native_ber_raw = safe_float(row.get("native_ber_raw"), default=0.0)

        spice_ber_contract = logistic_ber_from_snm(
            snm_mv=spice_snm_mv,
            center_mv=ber_contract_center_mv,
            slope_mv=ber_contract_slope_mv,
        )
        native_ber_contract = logistic_ber_from_snm(
            snm_mv=native_snm_mv,
            center_mv=ber_contract_center_mv,
            slope_mv=ber_contract_slope_mv,
        )

        row["spice_ber_contract"] = spice_ber_contract
        row["native_ber_contract"] = native_ber_contract
        row["delta_ber_contract"] = float(native_ber_contract) - float(spice_ber_contract)
        row["ber_contract_center_mv"] = float(ber_contract_center_mv)
        row["ber_contract_slope_mv"] = float(ber_contract_slope_mv)
        row["ber_contract_fit_samples"] = int(ber_fit_samples)

        if args.ber_contract_mode == "raw_native":
            row["spice_ber"] = spice_ber_raw
            row["native_ber"] = native_ber_raw
            row["delta_ber"] = float(native_ber_raw) - float(spice_ber_raw)
        else:
            row["spice_ber"] = spice_ber_contract
            row["native_ber"] = native_ber_contract
            row["delta_ber"] = float(native_ber_contract) - float(spice_ber_contract)

    spice_source_label = (
        f"pdk:{pdk_context.pdk_id}" if (args.spice_source == "pdk" and pdk_context is not None) else args.spice_source
    )
    write_csv(args.out_csv, rows)
    write_report(
        path=args.out_report,
        rows=rows,
        args=args,
        spice_source=spice_source_label,
        csv_path=args.out_csv,
        spice_proxy=spice_proxy,
        pdk_context=pdk_context,
        snm_noise_contract_summary=snm_noise_contract_summary,
    )

    print(f"[ok] wrote csv: {args.out_csv}")
    print(f"[ok] wrote report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
