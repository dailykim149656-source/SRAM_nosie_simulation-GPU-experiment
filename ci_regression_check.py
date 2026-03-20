"""End-to-end regression gate for native fidelity + SPICE correlation.

Runs:
1) native_hybrid_fidelity_check.py
2) spice_validation/run_spice_validation.py (ngspice + fitted proxy config)

Then enforces thresholds from a JSON config.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path
from statistics import fmean


REPO_ROOT = Path(__file__).resolve().parent


def run_cmd(cmd: list[str], cwd: Path) -> None:
    print("[run]", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(cwd), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(cmd)}")


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"json object expected: {path}")
    return data


def mean_abs(rows: list[dict[str, str]], key: str) -> float:
    values = [abs(float(r[key])) for r in rows]
    return fmean(values) if values else 0.0


def max_abs(rows: list[dict[str, str]], key: str) -> float:
    values = [abs(float(r[key])) for r in rows]
    return max(values) if values else 0.0


def mean_abs_log10_diff(
    rows: list[dict[str, str]],
    left_key: str,
    right_key: str,
    floor: float = 1e-18,
) -> float:
    values = []
    safe_floor = max(float(floor), 1e-30)
    for row in rows:
        left = max(float(row[left_key]), safe_floor)
        right = max(float(row[right_key]), safe_floor)
        values.append(abs(math.log10(left) - math.log10(right)))
    return fmean(values) if values else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Native/SPICE regression gate")
    parser.add_argument(
        "--threshold-config",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "calibration" / "ci_thresholds_hybrid.json",
    )
    parser.add_argument(
        "--spice-proxy-config",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "calibration" / "fitted_spice_proxy_hybrid.json",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "results" / "spice_vs_native_ci.csv",
    )
    parser.add_argument(
        "--out-report",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "reports" / "spice_correlation_ci.md",
    )
    parser.add_argument("--skip-fidelity", action="store_true")
    parser.add_argument("--skip-spice", action="store_true")
    args = parser.parse_args()

    cfg = load_json(args.threshold_config)
    fidelity_cfg = cfg.get("fidelity", {})
    spice_cfg = cfg.get("spice", {})

    python = sys.executable

    if not args.skip_fidelity:
        run_cmd(
            [
                python,
                "native_hybrid_fidelity_check.py",
                "--repeats",
                str(int(fidelity_cfg.get("repeats", 20))),
                "--monte-carlo-runs",
                str(int(fidelity_cfg.get("monte_carlo_runs", 25))),
                "--ber-delta-max",
                str(float(fidelity_cfg.get("ber_delta_max", 0.12))),
                "--noise-delta-max",
                str(float(fidelity_cfg.get("noise_delta_max", 0.05))),
                "--snm-delta-max",
                str(float(fidelity_cfg.get("snm_delta_max", 0.01))),
            ],
            REPO_ROOT,
        )

    if not args.skip_spice:
        run_cmd(
            [
                python,
                "spice_validation/run_spice_validation.py",
                "--spice-source",
                "ngspice",
                "--backend",
                str(spice_cfg.get("backend", "hybrid")),
                "--num-cells",
                str(int(spice_cfg.get("num_cells", 64))),
                "--monte-carlo-runs",
                str(int(spice_cfg.get("monte_carlo_runs", 40))),
                "--native-noise-enable",
                "true" if bool(spice_cfg.get("native_noise_enable", True)) else "false",
                "--native-variability-enable",
                "true" if bool(spice_cfg.get("native_variability_enable", True)) else "false",
                "--native-thermal-enable",
                "true" if bool(spice_cfg.get("native_thermal_enable", True)) else "false",
                "--native-seed",
                str(int(spice_cfg.get("native_seed", 20260218))),
                "--spice-proxy-config",
                str(args.spice_proxy_config),
                "--out-csv",
                str(args.out_csv),
                "--out-report",
                str(args.out_report),
                "--data-source",
                str(spice_cfg.get("data_source", "proxy-calibrated")),
            ],
            REPO_ROOT,
        )

        with args.out_csv.open("r", encoding="utf-8", newline="") as fp:
            rows = list(csv.DictReader(fp))
        if not rows:
            raise RuntimeError(f"no rows found in csv: {args.out_csv}")

        mae_snm_mv = mean_abs(rows, "delta_snm_mv")
        mae_noise = mean_abs(rows, "delta_noise")
        mae_ber = mean_abs(rows, "delta_ber")
        max_abs_ber_delta = max_abs(rows, "delta_ber")
        mae_log10_ber = mean_abs_log10_diff(rows, "native_ber", "spice_ber")

        print(
            "[metrics]",
            f"mae_snm_mv={mae_snm_mv:.6f}",
            f"mae_noise={mae_noise:.6f}",
            f"mae_ber={mae_ber:.6f}",
            f"mae_log10_ber={mae_log10_ber:.6f}",
            f"max_abs_ber_delta={max_abs_ber_delta:.6f}",
        )

        checks = [
            ("mae_snm_mv", mae_snm_mv, float(spice_cfg.get("mae_snm_mv_max", 12.0))),
            ("mae_noise", mae_noise, float(spice_cfg.get("mae_noise_max", 0.03))),
            ("mae_ber", mae_ber, float(spice_cfg.get("mae_ber_max", 0.04))),
            ("mae_log10_ber", mae_log10_ber, float(spice_cfg.get("mae_log10_ber_max", 0.35))),
            (
                "max_abs_ber_delta",
                max_abs_ber_delta,
                float(spice_cfg.get("max_abs_ber_delta_max", 0.06)),
            ),
        ]
        failures = [f"{name}: {value:.6f} > {limit:.6f}" for name, value, limit in checks if value > limit]
        if failures:
            raise RuntimeError("spice regression threshold failed: " + "; ".join(failures))

    print("[ok] regression gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
