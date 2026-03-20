"""Native hybrid fidelity regression check.

Compares:
1) strict native hybrid path
2) Python hybrid reference path

for the same PVT corners and reports BER/noise/SNM deltas.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from typing import Dict, List, Tuple

from native_backend import simulate_array


CONDITIONS: List[Tuple[str, float, float]] = [
    ("nominal", 300.0, 1.0),
    ("high_temp", 360.0, 1.0),
    ("low_v", 300.0, 0.8),
    ("worst", 360.0, 0.8),
]


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.fmean(values))


def _run_once(
    temperature: float,
    voltage: float,
    pattern: List[int],
    native: bool,
    monte_carlo_runs: int,
) -> Dict[str, float]:
    req = {
        "backend": "hybrid",
        "temperature": float(temperature),
        "voltage": float(voltage),
        "num_cells": int(len(pattern)),
        "input_data": list(pattern),
        "noise_enable": True,
        "variability_enable": True,
        "monte_carlo_runs": int(monte_carlo_runs),
        "width": 1.0,
        "length": 1.0,
        "include_thermal_noise": True,
        "require_native": bool(native),
        "prefer_hybrid_gate_logic": not native,
    }
    result = simulate_array(req)
    noise_values = [float(v) for v in result.get("noise_values", [])]
    snm_values = [float(v) for v in result.get("snm_values", [])]
    return {
        "ber": float(result.get("bit_error_rate", 0.0)),
        "noise": _mean(noise_values),
        "snm": _mean(snm_values),
    }


def _collect_stats(
    temperature: float,
    voltage: float,
    pattern: List[int],
    native: bool,
    repeats: int,
    monte_carlo_runs: int,
) -> Dict[str, float]:
    bers: List[float] = []
    noises: List[float] = []
    snms: List[float] = []

    for _ in range(repeats):
        one = _run_once(temperature, voltage, pattern, native, monte_carlo_runs)
        bers.append(one["ber"])
        noises.append(one["noise"])
        snms.append(one["snm"])

    return {"ber": _mean(bers), "noise": _mean(noises), "snm": _mean(snms)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid native fidelity regression checker")
    parser.add_argument("--repeats", type=int, default=20, help="repeats per condition")
    parser.add_argument("--monte-carlo-runs", type=int, default=25, help="MC runs per simulation")
    parser.add_argument(
        "--ber-delta-max",
        type=float,
        default=0.20,
        help="max allowed |native-ref| BER delta",
    )
    parser.add_argument(
        "--noise-delta-max",
        type=float,
        default=0.05,
        help="max allowed |native-ref| noise mean delta",
    )
    parser.add_argument(
        "--snm-delta-max",
        type=float,
        default=0.01,
        help="max allowed |native-ref| SNM mean delta (V)",
    )
    args = parser.parse_args()

    pattern = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1]
    failed = False

    header = (
        "condition         native_ber  ref_ber   d_ber    "
        "native_noise ref_noise d_noise  native_snm ref_snm d_snm"
    )
    print(header)
    print("-" * len(header))

    for name, temp, volt in CONDITIONS:
        native = _collect_stats(
            temperature=temp,
            voltage=volt,
            pattern=pattern,
            native=True,
            repeats=args.repeats,
            monte_carlo_runs=args.monte_carlo_runs,
        )
        reference = _collect_stats(
            temperature=temp,
            voltage=volt,
            pattern=pattern,
            native=False,
            repeats=args.repeats,
            monte_carlo_runs=args.monte_carlo_runs,
        )

        d_ber = abs(native["ber"] - reference["ber"])
        d_noise = abs(native["noise"] - reference["noise"])
        d_snm = abs(native["snm"] - reference["snm"])

        print(
            f"{name:<16} "
            f"{native['ber']:<10.6f} {reference['ber']:<8.6f} {d_ber:<8.6f} "
            f"{native['noise']:<12.6f} {reference['noise']:<9.6f} {d_noise:<8.6f} "
            f"{native['snm']:<10.6f} {reference['snm']:<8.6f} {d_snm:<8.6f}"
        )

        if d_ber > args.ber_delta_max or d_noise > args.noise_delta_max or d_snm > args.snm_delta_max:
            failed = True

    if failed:
        print(
            "\nFidelity check FAILED: one or more deltas exceeded thresholds "
            f"(ber={args.ber_delta_max}, noise={args.noise_delta_max}, snm={args.snm_delta_max})."
        )
        return 1

    print(
        "\nFidelity check PASSED within thresholds "
        f"(ber={args.ber_delta_max}, noise={args.noise_delta_max}, snm={args.snm_delta_max})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
