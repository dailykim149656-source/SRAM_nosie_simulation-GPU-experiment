"""Fit SPICE proxy coefficients from a correlation CSV.

This utility estimates coefficients for `sram6t_template.sp` proxy parameters:
- snm_scale_mv
- noise_scale
- ber_center_mv
- ber_slope_mv

It uses existing SPICE/native comparison data and writes a JSON config that can
be passed to `run_spice_validation.py --spice-proxy-config`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import fmean


def mae(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("length mismatch")
    if not a:
        return 0.0
    return fmean(abs(x - y) for x, y in zip(a, b))


def load_rows(path: Path) -> list[dict[str, float]]:
    rows_out: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            rows_out.append(
                {
                    "spice_snm_mv": float(row["spice_snm_mv"]),
                    "native_snm_mv": float(row["native_snm_mv"]),
                    "spice_noise": float(row["spice_noise"]),
                    "native_noise": float(row["native_noise"]),
                    "spice_ber": float(row["spice_ber"]),
                    "native_ber": float(row["native_ber"]),
                }
            )
    if not rows_out:
        raise ValueError(f"no rows in csv: {path}")
    return rows_out


def fit_scale(x: list[float], y: list[float], fallback: float) -> float:
    denom = sum(v * v for v in x)
    if denom <= 1e-18:
        return fallback
    return max(1e-12, sum(a * b for a, b in zip(x, y)) / denom)


def logistic_ber(snm_mv: float, center_mv: float, slope_mv: float) -> float:
    z = (snm_mv - center_mv) / max(slope_mv, 1e-9)
    if z > 60.0:
        return 0.0
    if z < -60.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(z))


def fit_ber_params(snm_mv: list[float], ber_target: list[float], center0: float, slope0: float) -> tuple[float, float]:
    min_snm = min(snm_mv)
    max_snm = max(snm_mv)
    best_center = center0
    best_slope = max(slope0, 1e-6)
    best_err = float("inf")

    center_start = min_snm - 80.0
    center_stop = max_snm + 80.0
    slope_values = [float(v) for v in range(2, 121)]  # mV

    center = center_start
    while center <= center_stop:
        for slope in slope_values:
            pred = [logistic_ber(v, center, slope) for v in snm_mv]
            err = mae(pred, ber_target)
            if err < best_err:
                best_err = err
                best_center = center
                best_slope = slope
        center += 1.0

    return best_center, best_slope


def clip_value(value: float, min_value: float, max_value: float) -> tuple[float, bool]:
    clipped = min(max(float(value), float(min_value)), float(max_value))
    return clipped, not math.isclose(clipped, float(value), rel_tol=1e-12, abs_tol=1e-12)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit SPICE proxy coefficients from correlation CSV")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("spice_validation/results/spice_vs_native_hybrid.csv"),
    )
    parser.add_argument(
        "--base-config",
        type=Path,
        default=Path("spice_validation/calibration/default_spice_proxy.json"),
    )
    parser.add_argument(
        "--out-config",
        type=Path,
        default=Path("spice_validation/calibration/fitted_spice_proxy.json"),
    )
    parser.add_argument("--snm-scale-min", type=float, default=100.0)
    parser.add_argument("--snm-scale-max", type=float, default=5000.0)
    parser.add_argument("--noise-scale-min", type=float, default=1e-4)
    parser.add_argument("--noise-scale-max", type=float, default=5.0)
    parser.add_argument("--ber-center-min", type=float, default=-200.0)
    parser.add_argument("--ber-center-max", type=float, default=400.0)
    parser.add_argument("--ber-slope-min", type=float, default=2.0)
    parser.add_argument("--ber-slope-max", type=float, default=200.0)
    args = parser.parse_args()

    base = json.loads(args.base_config.read_text(encoding="utf-8"))
    rows = load_rows(args.input_csv)

    spice_snm = [r["spice_snm_mv"] for r in rows]
    native_snm = [r["native_snm_mv"] for r in rows]
    spice_noise = [r["spice_noise"] for r in rows]
    native_noise = [r["native_noise"] for r in rows]
    spice_ber = [r["spice_ber"] for r in rows]
    native_ber = [r["native_ber"] for r in rows]

    base_snm_scale = float(base.get("snm_scale_mv", 500.0))
    base_noise_scale = float(base.get("noise_scale", 1.0))
    base_center = float(base.get("ber_center_mv", 120.0))
    base_slope = float(base.get("ber_slope_mv", 10.0))

    snm_core = [v / max(base_snm_scale, 1e-12) for v in spice_snm]
    noise_core = [v / max(base_noise_scale, 1e-12) for v in spice_noise]

    fitted_snm_scale = fit_scale(snm_core, native_snm, base_snm_scale)
    fitted_noise_scale = fit_scale(noise_core, native_noise, base_noise_scale)

    fitted_snm = [v * fitted_snm_scale for v in snm_core]
    fitted_center, fitted_slope = fit_ber_params(fitted_snm, native_ber, base_center, base_slope)
    fitted_ber = [logistic_ber(v, fitted_center, fitted_slope) for v in fitted_snm]

    snm_scale_bounded, snm_scale_clipped = clip_value(fitted_snm_scale, args.snm_scale_min, args.snm_scale_max)
    noise_scale_bounded, noise_scale_clipped = clip_value(fitted_noise_scale, args.noise_scale_min, args.noise_scale_max)
    ber_center_bounded, ber_center_clipped = clip_value(fitted_center, args.ber_center_min, args.ber_center_max)
    ber_slope_bounded, ber_slope_clipped = clip_value(fitted_slope, args.ber_slope_min, args.ber_slope_max)

    clipped_flags = {
        "snm_scale_mv": snm_scale_clipped,
        "noise_scale": noise_scale_clipped,
        "ber_center_mv": ber_center_clipped,
        "ber_slope_mv": ber_slope_clipped,
    }

    out = {
        "snm_scale_mv": float(snm_scale_bounded),
        "noise_scale": float(noise_scale_bounded),
        "noise_write_weight": float(base.get("noise_write_weight", 0.5)),
        "ber_center_mv": float(ber_center_bounded),
        "ber_slope_mv": float(ber_slope_bounded),
        "fit_metadata": {
            "bounded": True,
            "bounds": {
                "snm_scale_mv": [float(args.snm_scale_min), float(args.snm_scale_max)],
                "noise_scale": [float(args.noise_scale_min), float(args.noise_scale_max)],
                "ber_center_mv": [float(args.ber_center_min), float(args.ber_center_max)],
                "ber_slope_mv": [float(args.ber_slope_min), float(args.ber_slope_max)],
            },
            "clipped": clipped_flags,
        },
    }

    args.out_config.parent.mkdir(parents=True, exist_ok=True)
    args.out_config.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print("Fitted config written:", args.out_config.as_posix())
    print("SNM MAE baseline:", f"{mae(spice_snm, native_snm):.6f}", "fitted:", f"{mae(fitted_snm, native_snm):.6f}")
    print("Noise MAE baseline:", f"{mae(spice_noise, native_noise):.6f}", "fitted:", f"{mae([v * fitted_noise_scale for v in noise_core], native_noise):.6f}")
    print("BER MAE baseline:", f"{mae(spice_ber, native_ber):.6f}", "fitted:", f"{mae(fitted_ber, native_ber):.6f}")
    print("Bounded clip flags:", clipped_flags)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
