"""Phase 3 node-scaling runner.

Runs node/corner/PVT sweeps in strict native mode, applies node profile scaling,
then maps circuit metrics to system KPIs.

Outputs:
- reports/node_tradeoff.csv
- reports/node_scaling_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from native_backend import simulate_array
from workload_model import CircuitToSystemTranslator, WorkloadScenarios


DEFAULT_CORNER_FACTORS = {
    "tt": {"snm": 1.0, "noise": 1.0, "ber": 1.0, "leakage": 1.0},
    "ff": {"snm": 1.04, "noise": 0.95, "ber": 0.80, "leakage": 1.08},
    "ss": {"snm": 0.96, "noise": 1.05, "ber": 1.25, "leakage": 0.94},
}

DATA_SOURCE_CHOICES = (
    "proxy-calibrated",
    "foundry-pdk-pre-silicon",
    "predictive-pdk-pre-silicon",
    "model-card-calibrated",
    "silicon-correlated",
)


def parse_bool_arg(text: str) -> bool:
    token = str(text).strip().lower()
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {text}")


def parse_float_list(text: str) -> list[float]:
    values: list[float] = []
    for token in str(text).split(","):
        token = token.strip()
        if token:
            values.append(float(token))
    if not values:
        raise ValueError("at least one numeric value is required")
    return values


def parse_corner_list(text: str) -> list[str]:
    values: list[str] = []
    for token in str(text).split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token not in {"tt", "ff", "ss"}:
            raise ValueError(f"unsupported corner '{token}' (supported: tt,ff,ss)")
        values.append(token)
    if not values:
        raise ValueError("at least one corner is required")
    return values


def _require_keys(profile: dict, keys: list[str], source: Path) -> None:
    for key in keys:
        if key not in profile:
            raise ValueError(f"missing key '{key}' in node config: {source}")


def load_node_profiles(config_dir: Path) -> list[dict[str, object]]:
    files = sorted(config_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no node profile JSON files found in: {config_dir}")

    profiles: list[dict[str, object]] = []
    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError(f"node profile must be a JSON object: {path}")

        _require_keys(
            raw,
            [
                "node",
                "width_um",
                "length_um",
                "nominal_vdd",
                "leakage_mw_nominal",
                "snm_scale",
                "noise_scale",
                "ber_scale",
            ],
            path,
        )

        corner_factors = raw.get("corner_factors", {})
        if corner_factors and not isinstance(corner_factors, dict):
            raise ValueError(f"corner_factors must be an object: {path}")

        merged_corner_factors = dict(DEFAULT_CORNER_FACTORS)
        if isinstance(corner_factors, dict):
            for corner, vals in corner_factors.items():
                if corner not in merged_corner_factors:
                    continue
                if not isinstance(vals, dict):
                    continue
                base = dict(merged_corner_factors[corner])
                for key in ("snm", "noise", "ber", "leakage"):
                    if key in vals:
                        base[key] = float(vals[key])
                merged_corner_factors[corner] = base

        profile = {
            "node": str(raw["node"]),
            "width_um": float(raw["width_um"]),
            "length_um": float(raw["length_um"]),
            "nominal_vdd": float(raw["nominal_vdd"]),
            "leakage_mw_nominal": float(raw["leakage_mw_nominal"]),
            "snm_scale": float(raw["snm_scale"]),
            "noise_scale": float(raw["noise_scale"]),
            "ber_scale": float(raw["ber_scale"]),
            "corner_factors": merged_corner_factors,
            "source": str(path.as_posix()),
        }
        profiles.append(profile)

    return profiles


def workload_from_name(name: str):
    lookup = {
        "llama_7b_online": WorkloadScenarios.llama_7b_online,
        "llama_7b_batch": WorkloadScenarios.llama_7b_batch,
        "llama_13b_online": WorkloadScenarios.llama_13b_online,
        "llama_70b_mqa": WorkloadScenarios.llama_70b_mqa,
    }
    key = str(name).strip().lower()
    if key not in lookup:
        supported = ", ".join(sorted(lookup))
        raise ValueError(f"unsupported workload '{name}' (supported: {supported})")
    return lookup[key]()


def run_native_point(
    profile: dict[str, object],
    temp_k: float,
    vdd: float,
    backend: str,
    num_cells: int,
    monte_carlo_runs: int,
    noise_enable: bool,
    variability_enable: bool,
    thermal_enable: bool,
    seed: int | None,
) -> dict[str, object]:
    input_data = [i % 2 for i in range(max(num_cells, 1))]
    request = {
        "backend": backend,
        "temperature": float(temp_k),
        "voltage": float(vdd),
        "num_cells": max(num_cells, 1),
        "input_data": input_data,
        "noise_enable": bool(noise_enable),
        "variability_enable": bool(variability_enable),
        "monte_carlo_runs": max(monte_carlo_runs, 1),
        "width": float(profile["width_um"]),
        "length": float(profile["length_um"]),
        "include_thermal_noise": bool(thermal_enable),
        "require_native": True,
        "prefer_hybrid_gate_logic": False,
    }
    if seed is not None:
        request["seed"] = int(seed)

    result = simulate_array(request)
    exec_meta = result.get("_exec", {}) if isinstance(result, dict) else {}
    fallback = bool(exec_meta.get("fallback", True))
    if fallback:
        raise RuntimeError("native fallback detected; strict native requirement violated")

    snm_values = [float(v) for v in result.get("snm_values", [])]
    noise_values = [float(v) for v in result.get("noise_values", [])]

    return {
        "snm_mv_raw": (fmean(snm_values) * 1000.0) if snm_values else 0.0,
        "noise_raw": fmean(noise_values) if noise_values else 0.0,
        "ber_raw": float(result.get("bit_error_rate", 0.0)),
        "backend_label": str(result.get("backend", "unknown")),
        "native_engine": str(exec_meta.get("selected", "unknown")),
        "thermal_sigma": float(result.get("thermal_sigma", 0.0)),
    }


def apply_node_corner_scaling(
    profile: dict[str, object],
    corner: str,
    temp_k: float,
    vdd: float,
    raw: dict[str, object],
) -> dict[str, float]:
    corner_factors = profile["corner_factors"].get(corner, DEFAULT_CORNER_FACTORS[corner])

    snm_mv = float(raw["snm_mv_raw"]) * float(profile["snm_scale"]) * float(corner_factors["snm"])
    noise = float(raw["noise_raw"]) * float(profile["noise_scale"]) * float(corner_factors["noise"])
    ber = float(raw["ber_raw"]) * float(profile["ber_scale"]) * float(corner_factors["ber"])
    ber = max(0.0, min(1.0, ber))

    nominal_vdd = max(float(profile["nominal_vdd"]), 1e-9)
    leakage_mw = float(profile["leakage_mw_nominal"]) * (float(vdd) / nominal_vdd) ** 2
    leakage_mw *= float(corner_factors["leakage"])

    return {
        "snm_mv": snm_mv,
        "noise": noise,
        "ber": ber,
        "leakage_mw": leakage_mw,
        "temp_k": float(temp_k),
        "vdd": float(vdd),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _node_nm(node_name: str) -> int:
    digits = "".join(ch for ch in node_name if ch.isdigit())
    return int(digits) if digits else 0


def summarize_by_node(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["node"]), []).append(row)

    summary: list[dict[str, object]] = []
    for node, items in grouped.items():
        summary.append(
            {
                "node": node,
                "points": len(items),
                "mean_snm_mv": fmean(float(i["snm_mv"]) for i in items),
                "mean_ber": fmean(float(i["ber"]) for i in items),
                "mean_noise": fmean(float(i["noise"]) for i in items),
                "mean_tail_latency_ms": fmean(float(i["tail_latency_ms"]) for i in items),
                "mean_energy_per_token_uj": fmean(float(i["energy_per_token_uj"]) for i in items),
                "mean_tokens_per_sec": fmean(float(i["tokens_per_second"]) for i in items),
                "mean_accuracy_deg_pct": fmean(float(i["accuracy_degradation_percent"]) for i in items),
                "accept_rate": fmean(1.0 if str(i["is_acceptable"]).lower() == "true" else 0.0 for i in items),
            }
        )

    summary.sort(key=lambda rec: _node_nm(str(rec["node"])), reverse=True)
    return summary


def write_report(
    path: Path,
    rows: list[dict[str, object]],
    summary: list[dict[str, object]],
    workload_name: str,
    backend: str,
    config_dir: Path,
    data_source: str,
) -> None:
    lines: list[str] = [
        "# Node Scaling Report (Phase 3)",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Data source: `{data_source}`",
        f"- Workload profile: `{workload_name}`",
        f"- Native backend: `{backend}`",
        f"- Node config dir: `{config_dir.as_posix()}`",
        f"- Total sweep points: `{len(rows)}`",
        "",
        "## Node Summary",
        "",
        "| Node | Points | Mean SNM (mV) | Mean BER | Mean Latency (ms) | Mean Energy/token (uJ) | Mean Tok/s | Accept Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary:
        lines.append(
            "| "
            f"{row['node']} | {int(row['points'])} | {float(row['mean_snm_mv']):.3f} | {float(row['mean_ber']):.6e} "
            f"| {float(row['mean_tail_latency_ms']):.3f} | {float(row['mean_energy_per_token_uj']):.3f} "
            f"| {float(row['mean_tokens_per_sec']):.3f} | {100.0 * float(row['accept_rate']):.1f}% |"
        )

    if len(summary) >= 2:
        largest = summary[0]
        smallest = summary[-1]

        def pct_change(old: float, new: float) -> float:
            if abs(old) < 1e-12:
                return 0.0
            return (new - old) / old * 100.0

        snm_delta = pct_change(float(largest["mean_snm_mv"]), float(smallest["mean_snm_mv"]))
        ber_delta = pct_change(float(largest["mean_ber"]), float(smallest["mean_ber"]))
        lat_delta = pct_change(float(largest["mean_tail_latency_ms"]), float(smallest["mean_tail_latency_ms"]))
        en_delta = pct_change(float(largest["mean_energy_per_token_uj"]), float(smallest["mean_energy_per_token_uj"]))

        lines.extend(
            [
                "",
                "## Scaling Trend",
                "",
                f"- Compared to `{largest['node']}`, `{smallest['node']}` changes:",
                f"  - SNM: {snm_delta:.2f}%",
                f"  - BER: {ber_delta:.2f}%",
                f"  - Tail latency: {lat_delta:.2f}%",
                f"  - Energy/token: {en_delta:.2f}%",
                "",
                "## Notes",
                "",
                "- Data source must match the report header (`proxy-calibrated|foundry-pdk-pre-silicon|predictive-pdk-pre-silicon|model-card-calibrated|silicon-correlated`).",
            ]
        )

        if data_source == "proxy-calibrated":
            lines.extend(
                [
                    "- Node profiles are proxy calibrations (not foundry signoff models).",
                    "- Use this report for trend analysis and reproducibility checks, then replace with PDK-calibrated values.",
                ]
            )
        elif data_source == "foundry-pdk-pre-silicon":
            lines.extend(
                [
                    "- Correlated to foundry PDK decks in pre-silicon conditions.",
                    "- Silicon bring-up correlation is required before claiming silicon-correlated accuracy.",
                ]
            )
        elif data_source == "predictive-pdk-pre-silicon":
            lines.extend(
                [
                    "- Correlated to predictive PDK decks in pre-silicon conditions.",
                    "- Treat node trends as directional guidance, not foundry signoff evidence.",
                ]
            )
        elif data_source == "model-card-calibrated":
            lines.extend(
                [
                    "- Calibrated with model-card-level data (no full foundry macro deck correlation).",
                    "- Use guard-bands for safety-critical corners before architectural decisions.",
                ]
            )
        else:
            lines.append("- Silicon-correlated mode: ensure lot/wafer/temperature coverage is documented separately.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 3 node scaling sweep")
    parser.add_argument("--config-dir", type=Path, default=REPO_ROOT / "configs" / "nodes")
    parser.add_argument("--backend", choices=["standard", "hybrid"], default="hybrid")
    parser.add_argument("--corners", default="tt,ff,ss")
    parser.add_argument("--temps-k", default="300,330,360")
    parser.add_argument("--vdds", default="auto", help="'auto' or comma-separated list, e.g. 0.65,0.75,0.85")
    parser.add_argument("--num-cells", type=int, default=64)
    parser.add_argument("--monte-carlo-runs", type=int, default=40)
    parser.add_argument("--noise-enable", default="true", help="true|false")
    parser.add_argument("--variability-enable", default="true", help="true|false")
    parser.add_argument("--thermal-enable", default="true", help="true|false")
    parser.add_argument("--seed", type=int, default=20260219)
    parser.add_argument(
        "--data-source",
        choices=list(DATA_SOURCE_CHOICES),
        default="proxy-calibrated",
    )
    parser.add_argument(
        "--workload",
        default="llama_7b_online",
        choices=["llama_7b_online", "llama_7b_batch", "llama_13b_online", "llama_70b_mqa"],
    )
    parser.add_argument("--out-csv", type=Path, default=REPO_ROOT / "reports" / "node_tradeoff.csv")
    parser.add_argument("--out-report", type=Path, default=REPO_ROOT / "reports" / "node_scaling_report.md")
    args = parser.parse_args()

    corners = parse_corner_list(args.corners)
    temps_k = parse_float_list(args.temps_k)
    global_vdds: list[float] | None = None
    if str(args.vdds).strip().lower() != "auto":
        global_vdds = parse_float_list(args.vdds)
    noise_enable = parse_bool_arg(args.noise_enable)
    variability_enable = parse_bool_arg(args.variability_enable)
    thermal_enable = parse_bool_arg(args.thermal_enable)

    profiles = load_node_profiles(args.config_dir)

    workload = workload_from_name(args.workload)
    translator = CircuitToSystemTranslator(workload)

    rows: list[dict[str, object]] = []
    case_index = 0

    for profile in profiles:
        if global_vdds is not None:
            node_vdds = list(global_vdds)
        else:
            nominal_vdd = float(profile["nominal_vdd"])
            auto_vdds = [max(0.50, nominal_vdd - 0.10), nominal_vdd, min(1.10, nominal_vdd + 0.10)]
            node_vdds = sorted({round(v, 2) for v in auto_vdds})

        for corner in corners:
            for temp_k in temps_k:
                for vdd in node_vdds:
                    seed = int(args.seed + case_index) if args.seed is not None else None
                    raw = run_native_point(
                        profile=profile,
                        temp_k=temp_k,
                        vdd=vdd,
                        backend=args.backend,
                        num_cells=args.num_cells,
                        monte_carlo_runs=args.monte_carlo_runs,
                        noise_enable=noise_enable,
                        variability_enable=variability_enable,
                        thermal_enable=thermal_enable,
                        seed=seed,
                    )
                    scaled = apply_node_corner_scaling(profile, corner, temp_k, vdd, raw)
                    kpi = translator.translate_to_system_kpis(
                        snm_mv=float(scaled["snm_mv"]),
                        vmin_v=float(vdd),
                        leakage_mw=float(scaled["leakage_mw"]),
                        temp_c=float(temp_k) - 273.15,
                    )
                    system = kpi["system_kpis"]

                    case_id = f"{profile['node']}_{corner}_t{int(round(temp_k))}_v{vdd:.2f}".replace(".", "p")
                    rows.append(
                        {
                            "case_id": case_id,
                            "node": profile["node"],
                            "corner": corner,
                            "temp_k": float(temp_k),
                            "vdd": float(vdd),
                            "snm_mv": float(scaled["snm_mv"]),
                            "noise": float(scaled["noise"]),
                            "ber": float(scaled["ber"]),
                            "leakage_mw": float(scaled["leakage_mw"]),
                            "tail_latency_ms": float(system["tail_latency_ms"]),
                            "energy_per_token_uj": float(system["energy_per_token_uj"]),
                            "tokens_per_second": float(system["tokens_per_second"]),
                            "accuracy_degradation_percent": float(system["accuracy_degradation_percent"]),
                            "is_acceptable": bool(kpi["is_acceptable"]),
                            "native_backend_label": raw["backend_label"],
                            "native_engine": raw["native_engine"],
                            "config_source": profile["source"],
                            "data_source": args.data_source,
                        }
                    )
                    case_index += 1

    write_csv(args.out_csv, rows)
    summary = summarize_by_node(rows)
    write_report(
        path=args.out_report,
        rows=rows,
        summary=summary,
        workload_name=args.workload,
        backend=args.backend,
        config_dir=args.config_dir,
        data_source=args.data_source,
    )

    print(f"[ok] wrote csv: {args.out_csv}")
    print(f"[ok] wrote report: {args.out_report}")
    print(f"[ok] points: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
