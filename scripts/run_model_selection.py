"""Phase 2 model-selection runner using SPICE-correlated data.

Outputs:
- reports/model_pareto.csv
- reports/model_selection_report.md
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml_benchmark import SRAMModelBenchmark

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


def compute_pareto_frontier(model_records: list[dict[str, object]]) -> set[str]:
    """Pareto frontier on (maximize mean_r2, minimize mean_infer_ms)."""
    frontier: set[str] = set()
    for idx, left in enumerate(model_records):
        left_r2 = float(left["mean_r2"])
        left_infer = float(left["mean_infer_ms"])
        dominated = False
        for jdx, right in enumerate(model_records):
            if idx == jdx:
                continue
            right_r2 = float(right["mean_r2"])
            right_infer = float(right["mean_infer_ms"])
            better_or_equal = (right_r2 >= left_r2) and (right_infer <= left_infer)
            strictly_better = (right_r2 > left_r2) or (right_infer < left_infer)
            if better_or_equal and strictly_better:
                dominated = True
                break
        if not dominated:
            frontier.add(str(left["model"]))
    return frontier


def pick_recommended_model(
    model_records: list[dict[str, object]],
    frontier_models: set[str],
    r2_tolerance: float = 0.02,
    latency_multiplier: float = 2.0,
) -> tuple[dict[str, object], float, float, float]:
    frontier = [record for record in model_records if str(record["model"]) in frontier_models]
    if not frontier:
        frontier = list(model_records)

    best_r2 = max(float(record["mean_r2"]) for record in frontier)
    r2_floor = best_r2 - abs(float(r2_tolerance))
    quality_candidates = [record for record in frontier if float(record["mean_r2"]) >= r2_floor]
    if not quality_candidates:
        quality_candidates = frontier

    fastest = min(float(record["mean_infer_ms"]) for record in quality_candidates)
    latency_cap = max(fastest * latency_multiplier, fastest)

    candidates = [record for record in quality_candidates if float(record["mean_infer_ms"]) <= latency_cap]
    if not candidates:
        candidates = quality_candidates

    candidates = sorted(
        candidates,
        key=lambda rec: (
            -float(rec["mean_r2"]),
            float(rec["mean_infer_ms"]),
            float(rec["mean_mae"]),
            int(rec["param_count"]),
        ),
    )
    return candidates[0], r2_floor, best_r2, latency_cap


def compute_monotonic_violation_rates(dataset: dict[str, object]) -> dict[str, float]:
    rows = dataset.get("data", [])
    targets = dataset.get("targets", {})
    if not isinstance(rows, list) or not isinstance(targets, dict) or not rows:
        return {}

    fail_like_targets = [name for name in ("ber", "read_fail", "write_fail", "noise_sigma") if name in targets]
    if not fail_like_targets:
        return {}

    grouped_indices: dict[tuple[str, float], list[int]] = {}
    for idx, row in enumerate(rows):
        corner = str(row.get("corner", "")).strip().lower()
        temp_k = round(float(row.get("temp_k", 0.0)), 2)
        grouped_indices.setdefault((corner, temp_k), []).append(idx)

    rates: dict[str, float] = {}
    for target_name in fail_like_targets:
        values = [float(v) for v in targets[target_name]]
        violations = 0
        comparisons = 0
        for _, indices in grouped_indices.items():
            ordered = sorted(indices, key=lambda i: float(rows[i]["vdd"]))
            if len(ordered) < 2:
                continue
            for left_idx, right_idx in zip(ordered[:-1], ordered[1:]):
                low_vdd_val = values[left_idx]
                high_vdd_val = values[right_idx]
                comparisons += 1
                if low_vdd_val < high_vdd_val:
                    violations += 1
        if comparisons > 0:
            rates[target_name] = violations / comparisons
    return rates


def write_pareto_csv(
    path: Path,
    model_records: list[dict[str, object]],
    frontier_models: set[str],
) -> None:
    target_names: list[str] = []
    if model_records:
        target_names = [str(name) for name in model_records[0]["targets"].keys()]

    rows: list[dict[str, object]] = []
    for rank, record in enumerate(model_records, start=1):
        targets = record["targets"]
        base_row: dict[str, object] = {
            "rank": rank,
            "model": record["model"],
            "pareto_optimal": str(record["model"]) in frontier_models,
            "mean_r2": float(record["mean_r2"]),
            "mean_rmse": float(record["mean_rmse"]),
            "mean_mae": float(record["mean_mae"]),
            "mean_train_ms": float(record["mean_train_ms"]),
            "mean_infer_ms": float(record["mean_infer_ms"]),
            "mean_r2_unweighted": float(record.get("mean_r2_unweighted", record["mean_r2"])),
            "mean_rmse_unweighted": float(record.get("mean_rmse_unweighted", record["mean_rmse"])),
            "mean_mae_unweighted": float(record.get("mean_mae_unweighted", record["mean_mae"])),
            "mean_train_ms_unweighted": float(record.get("mean_train_ms_unweighted", record["mean_train_ms"])),
            "mean_infer_ms_unweighted": float(record.get("mean_infer_ms_unweighted", record["mean_infer_ms"])),
            "param_count": int(record["param_count"]),
            "target_count": int(record.get("target_count", len(targets))),
        }
        for target_name in target_names:
            metric = targets[target_name]
            safe_name = target_name.replace(" ", "_")
            base_row[f"{safe_name}_r2"] = float(metric["r2"])
            base_row[f"{safe_name}_mae"] = float(metric["mae"])
            base_row[f"{safe_name}_rmse"] = float(metric["rmse"])
        rows.append(base_row)

    if not rows:
        raise ValueError("no benchmark rows to write")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    benchmark_result: dict[str, object],
    model_records: list[dict[str, object]],
    frontier_models: set[str],
    recommended_model: dict[str, object],
    r2_floor: float,
    best_r2: float,
    latency_cap: float,
    r2_tolerance: float,
    latency_multiplier: float,
    input_csv: Path,
    target_source: str,
    data_source: str,
    monotonic_rates: dict[str, float],
) -> None:
    meta = benchmark_result["meta"]
    n_samples = int(meta.get("n_samples", 0))
    feature_names = meta.get("feature_names", [])
    target_names = [str(name) for name in meta.get("target_names", list(model_records[0]["targets"].keys()))]
    n_folds = model_records[0]["targets"][target_names[0]].get("n_folds_used", meta.get("n_folds_requested", "n/a"))
    risk_weighting = bool(meta.get("risk_weighting", False))
    split_mode = str(meta.get("split_mode", "random"))
    target_clip_quantile = float(meta.get("target_clip_quantile", 0.0))
    target_normalize = bool(meta.get("target_normalize", False))
    target_prob_logit = bool(meta.get("target_prob_logit", False))
    fail_aux_split = bool(meta.get("fail_aux_split", False))
    fail_aux_profile = str(meta.get("fail_aux_profile", "default"))
    fail_aux_profile_requested = str(meta.get("fail_aux_profile_requested", fail_aux_profile))
    pdk_id = str(meta.get("pdk_id", "unknown"))
    r2_clip_min = float(meta.get("r2_clip_min", -10.0))
    r2_clip_max = float(meta.get("r2_clip_max", 1.0))
    target_importance = meta.get("target_importance", {})
    target_importance_text = ", ".join(
        f"{name}={float(value):.2f}"
        for name, value in (target_importance.items() if isinstance(target_importance, dict) else [])
    )
    if not target_importance_text:
        target_importance_text = "n/a"

    lines: list[str] = [
        "# Model Selection Report (Phase 2)",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Data source: `{data_source}`",
        f"- Input CSV: `{input_csv.as_posix()}`",
        f"- PDK id: `{pdk_id}`",
        f"- Target Source: `{target_source}`",
        f"- Targets: `{', '.join(target_names)}`",
        f"- Risk weighting: `{risk_weighting}`",
        f"- Split mode: `{split_mode}`",
        f"- Target clip quantile: `{target_clip_quantile}`",
        f"- Target normalize: `{target_normalize}`",
        f"- Target prob-logit: `{target_prob_logit}`",
        f"- Fail aux split (`read_fail/write_fail` dedicated heads): `{fail_aux_split}`",
        f"- Fail aux profile (requested -> resolved): `{fail_aux_profile_requested} -> {fail_aux_profile}`",
        f"- R2 clip range: `[{r2_clip_min}, {r2_clip_max}]`",
        f"- Target importance (weighted aggregation): `{target_importance_text}`",
        f"- Samples: `{n_samples}`",
        f"- Features: `{', '.join(str(v) for v in feature_names)}`",
        f"- Cross-validation folds used: `{n_folds}`",
        "",
        "## Leaderboard",
        "",
        "| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]

    for rank, record in enumerate(model_records, start=1):
        model_name = str(record["model"])
        pareto = "yes" if model_name in frontier_models else "no"
        lines.append(
            "| "
            f"{rank} | {model_name} | {float(record['mean_r2']):.6f} | {float(record['mean_mae']):.6f} "
            f"| {float(record['mean_infer_ms']):.6f} | {int(record['param_count'])} | {pareto} |"
        )

    rec_name = str(recommended_model["model"])
    rec_targets = recommended_model["targets"]

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- Recommended model: **{rec_name}**",
            f"- Rule step 1 (quality): Pareto models with R2 >= `{r2_floor:.6f}` (best Pareto R2 `{best_r2:.6f}` - tolerance `{r2_tolerance:.6f}`)",
            f"- Rule step 2 (speed): among quality candidates, keep models within `{latency_cap:.6f}` ms/sample ({latency_multiplier:.2f}x fastest quality latency), then choose best R2",
            "",
            "| Target | R2 | RMSE | MAE |",
            "|---|---:|---:|---:|",
        ]
    )
    for target_name in target_names:
        metric = rec_targets[target_name]
        lines.append(
            f"| {target_name} | {float(metric['r2']):.6f} | {float(metric['rmse']):.6f} | {float(metric['mae']):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This report benchmarks model families under identical features/splits/metrics.",
            "- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.",
            "- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.",
        ]
    )
    if monotonic_rates:
        lines.extend(
            [
                "",
                "## Monotonic Sanity (Dataset)",
                "",
                "| Target | Violation Rate |",
                "|---|---:|",
            ]
        )
        for target_name, rate in monotonic_rates.items():
            lines.append(f"| {target_name} | {rate:.6f} |")
        lines.extend(
            [
                "",
                "- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 2 model selection from SPICE correlation CSV")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "results" / "spice_vs_native_hybrid_fitted.csv",
    )
    parser.add_argument(
        "--target-source",
        choices=["spice", "native", "delta", "spice_v2", "native_v2", "delta_v2"],
        default="spice",
    )
    parser.add_argument("--risk-weighting", default="true", help="true|false")
    parser.add_argument("--split-mode", choices=["random", "group_pvt"], default="group_pvt")
    parser.add_argument("--target-clip-quantile", type=float, default=0.01)
    parser.add_argument("--target-normalize", default="true", help="true|false")
    parser.add_argument("--target-prob-logit", default="true", help="true|false")
    parser.add_argument("--fail-aux-split", default="false", help="true|false")
    parser.add_argument("--fail-aux-profile", default="auto", help="auto|default|sky130|gf180mcu|freepdk45_openram")
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--r2-tolerance", type=float, default=0.02)
    parser.add_argument("--latency-multiplier", type=float, default=2.0)
    parser.add_argument(
        "--data-source",
        choices=list(DATA_SOURCE_CHOICES),
        default="proxy-calibrated",
    )
    parser.add_argument(
        "--pareto-csv",
        type=Path,
        default=REPO_ROOT / "reports" / "model_pareto.csv",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=REPO_ROOT / "reports" / "model_selection_report.md",
    )
    args = parser.parse_args()
    args.risk_weighting = parse_bool_arg(args.risk_weighting)
    args.target_normalize = parse_bool_arg(args.target_normalize)
    args.target_prob_logit = parse_bool_arg(args.target_prob_logit)
    args.fail_aux_split = parse_bool_arg(args.fail_aux_split)
    args.fail_aux_profile = str(args.fail_aux_profile).strip().lower()

    dataset = SRAMModelBenchmark.load_spice_csv_dataset(
        args.input_csv,
        target_source=args.target_source,
        risk_weighting=args.risk_weighting,
        split_mode=args.split_mode,
        target_clip_quantile=float(args.target_clip_quantile),
        target_normalize=bool(args.target_normalize),
        target_prob_logit=bool(args.target_prob_logit),
        fail_aux_split=bool(args.fail_aux_split),
        fail_aux_profile=str(args.fail_aux_profile),
    )
    benchmark = SRAMModelBenchmark(
        n_samples=int(dataset["meta"]["n_samples"]),
        n_folds=max(2, int(args.n_folds)),
        random_state=int(args.random_state),
    )
    result = benchmark.run_benchmark(dataset=dataset)
    model_records = list(result["model_records"])
    if not model_records:
        raise RuntimeError("benchmark returned no model records")

    frontier_models = compute_pareto_frontier(model_records)
    recommended_model, r2_floor, best_r2, latency_cap = pick_recommended_model(
        model_records=model_records,
        frontier_models=frontier_models,
        r2_tolerance=float(args.r2_tolerance),
        latency_multiplier=float(args.latency_multiplier),
    )

    write_pareto_csv(args.pareto_csv, model_records, frontier_models)
    monotonic_rates = compute_monotonic_violation_rates(dataset)
    write_report(
        path=args.report_path,
        benchmark_result=result,
        model_records=model_records,
        frontier_models=frontier_models,
        recommended_model=recommended_model,
        r2_floor=r2_floor,
        best_r2=best_r2,
        latency_cap=latency_cap,
        r2_tolerance=float(args.r2_tolerance),
        latency_multiplier=float(args.latency_multiplier),
        input_csv=args.input_csv,
        target_source=args.target_source,
        data_source=args.data_source,
        monotonic_rates=monotonic_rates,
    )

    print(f"[ok] wrote pareto csv: {args.pareto_csv}")
    print(f"[ok] wrote report: {args.report_path}")
    print(f"[ok] recommended model: {recommended_model['model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
