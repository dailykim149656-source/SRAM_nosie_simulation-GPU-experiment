"""Build Gate B summary from reproduced correlation CSVs and baseline model reports."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def mean_abs(rows: list[dict[str, str]], key: str) -> float:
    values = [abs(float(row[key])) for row in rows]
    return sum(values) / len(values) if values else 0.0


def mean_abs_log10_diff(rows: list[dict[str, str]], left_key: str, right_key: str) -> float:
    floor = 1e-18
    values: list[float] = []
    for row in rows:
        left = max(float(row[left_key]), floor)
        right = max(float(row[right_key]), floor)
        values.append(abs(math.log10(left) - math.log10(right)))
    return sum(values) / len(values) if values else 0.0


def parse_model_pareto_best_infer_ms(path: Path) -> float:
    with path.open("r", encoding="utf-8", newline="") as fp:
        rows = list(csv.DictReader(fp))
    if not rows:
        raise ValueError(f"empty pareto csv: {path}")
    return min(float(row["mean_infer_ms"]) for row in rows)


def fmt(value: float) -> str:
    return f"{float(value):.6f}"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, object]], thresholds: dict[str, float], report_glob: str, pareto_dir: Path) -> None:
    lines = [
        "# Gate B Summary",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Report glob: `{report_glob}`",
        f"- Pareto dir: `{pareto_dir.as_posix()}`",
        (
            "- Thresholds: "
            f"snm<={thresholds['snm_mae_mv_max']}, "
            f"noise_sigma<={thresholds['noise_sigma_mae_max']}, "
            f"log10_ber<={thresholds['log10_ber_mae_max']}, "
            f"max_delta_ber<={thresholds['max_abs_ber_delta_max']}, "
            f"latency_gain>={thresholds['latency_gain_min']}"
        ),
        "",
        "| PDK | MAE SNM | MAE Noise Sigma | MAE log10 BER | Max Delta BER | Best Infer ms | Latency Gain x | Gate B |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['pdk_id']} | {fmt(row['mae_snm_mv'])} | {fmt(row['mae_noise_sigma'])} | {fmt(row['mae_log10_ber'])} | "
            f"{fmt(row['max_abs_delta_ber'])} | {fmt(row['best_infer_ms'])} | {fmt(row['latency_gain_x'])} | {row['gate_b']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Gate B summary from current outputs")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--report-glob", default="spice_correlation_pdk_*.md")
    parser.add_argument("--snm-mae-mv-max", type=float, default=10.0)
    parser.add_argument("--noise-sigma-mae-max", type=float, default=0.02)
    parser.add_argument("--log10-ber-mae-max", type=float, default=0.35)
    parser.add_argument("--max-abs-ber-delta-max", type=float, default=0.05)
    parser.add_argument("--latency-gain-min", type=float, default=50.0)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    args = parser.parse_args()

    thresholds = {
        "snm_mae_mv_max": float(args.snm_mae_mv_max),
        "noise_sigma_mae_max": float(args.noise_sigma_mae_max),
        "log10_ber_mae_max": float(args.log10_ber_mae_max),
        "max_abs_ber_delta_max": float(args.max_abs_ber_delta_max),
        "latency_gain_min": float(args.latency_gain_min),
    }

    rows: list[dict[str, object]] = []
    for csv_path in sorted(args.results_dir.glob("spice_vs_native_pdk_*.csv")):
        with csv_path.open("r", encoding="utf-8", newline="") as fp:
            data_rows = list(csv.DictReader(fp))
        if not data_rows:
            continue
        pdk_id = str(data_rows[0].get("pdk_id", "")).strip() or csv_path.stem.replace("spice_vs_native_pdk_", "")

        baseline_pareto = args.baseline_dir / pdk_id / "model_pareto.csv"
        best_infer_ms = parse_model_pareto_best_infer_ms(baseline_pareto)
        mean_spice_runtime_ms = sum(float(row["spice_runtime_ms"]) for row in data_rows) / len(data_rows)
        latency_gain = mean_spice_runtime_ms / best_infer_ms if best_infer_ms > 0.0 else 0.0
        max_abs_delta_ber = max(abs(float(row["delta_ber"])) for row in data_rows)
        mae_snm_mv = mean_abs(data_rows, "delta_snm_mv")
        mae_noise_sigma = mean_abs(data_rows, "delta_noise_sigma")
        mae_log10_ber = mean_abs_log10_diff(data_rows, "native_ber", "spice_ber")
        gate_b = (
            mae_snm_mv <= thresholds["snm_mae_mv_max"]
            and mae_noise_sigma <= thresholds["noise_sigma_mae_max"]
            and mae_log10_ber <= thresholds["log10_ber_mae_max"]
            and max_abs_delta_ber <= thresholds["max_abs_ber_delta_max"]
            and latency_gain >= thresholds["latency_gain_min"]
        )
        rows.append(
            {
                "pdk_id": pdk_id,
                "mae_snm_mv": mae_snm_mv,
                "mae_noise_sigma": mae_noise_sigma,
                "mae_log10_ber": mae_log10_ber,
                "max_abs_delta_ber": max_abs_delta_ber,
                "best_infer_ms": best_infer_ms,
                "latency_gain_x": latency_gain,
                "gate_b": "pass" if gate_b else "fail",
            }
        )

    write_csv(args.out_csv, rows)
    write_report(
        args.out_report,
        rows,
        thresholds=thresholds,
        report_glob=args.report_glob,
        pareto_dir=args.baseline_dir,
    )
    print(f"[ok] wrote csv: {args.out_csv}")
    print(f"[ok] wrote report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
