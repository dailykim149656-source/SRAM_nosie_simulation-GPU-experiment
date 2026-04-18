"""Artifact writers for analytical benchmark suites."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from benchmarks.schema import normalize_lane_name, normalize_fidelity_pair_name, validate_report_text


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_results_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_report_markdown(
    *,
    metadata: dict[str, object],
    rows: list[dict[str, object]],
    fidelity_records: list[dict[str, object]],
) -> str:
    lines: list[str] = [
        "# SRAM Analytical Benchmark Report",
        "",
        f"- Suite: `{metadata['suite']}`",
        f"- Device mode: `{metadata['device_mode']}`",
        f"- Seed: `{metadata['seed']}`",
        f"- Warmup / repeats: `{metadata['warmup_runs']}` / `{metadata['repeat_runs']}`",
        f"- Validation scope: `{metadata.get('validation_scope', 'unknown')}`",
        f"- Claim level: `{metadata.get('claim_level', 'unknown')}`",
        f"- Selected artifact files: `{', '.join(str(name) for name in metadata['artifact_files'])}`",
        "",
        "## Environment",
        "",
        f"- Python: `{metadata['env']['python_version']}`",
        f"- Platform: `{metadata['env']['platform']}`",
        f"- Torch: `{metadata['env'].get('torch_version') or 'unavailable'}`",
        f"- Torch build tag: `{metadata['env'].get('torch_build_tag') or 'none'}`",
        f"- Accelerator available: `{metadata['env'].get('accelerator_available')}`",
        f"- Accelerator runtime: `{metadata['env'].get('accelerator_runtime_kind')}`",
        f"- Accelerator device: `{metadata['env'].get('accelerator_device_display_name')}`",
        f"- CUDA version: `{metadata['env'].get('cuda_version') or 'none'}`",
        f"- HIP version: `{metadata['env'].get('hip_version') or 'none'}`",
        "",
        "## Results",
        "",
        "| Case | Lane | Status | Engine | Backend | Runtime | Device | Median Wall Clock (s) | Throughput (samples/s) | Mean Prediction |",
        "|---|---|---|---|---|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['case_id']} | {normalize_lane_name(str(row['lane']))} | {row['status']} | {row['selected_engine']} | "
            f"{row.get('backend_kind', 'unknown')} | {row.get('runtime_kind', 'unknown')} | "
            f"{row.get('device_display_name', row['device_name'])} | "
            f"{float(row['wall_clock_sec']):.6f} | {float(row['throughput_samples_per_sec']):.3f} | "
            f"{float(row['mean_prediction']):.6f} |"
        )

    lines.extend(
        [
            "",
            "## Fidelity Summary",
            "",
            "| Pair | Status | Max Abs Delta | Mean Abs Delta | Threshold Max | Threshold Mean |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for record in fidelity_records:
        lines.append(
            "| "
            f"{normalize_fidelity_pair_name(str(record['pair']))} | {record['status']} | {float(record['max_abs_delta']):.6e} | "
            f"{float(record['mean_abs_delta']):.6e} | {float(record['threshold_max_abs_delta']):.6e} | "
            f"{float(record['threshold_mean_abs_delta']):.6e} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `cpu_existing` uses `AnalyticalSRAMModel.generate_dataset()` with the fitted perceptron `.predict()` path.",
            "- `cpu_numpy` uses chunked analytical generation plus explicit NumPy forward.",
            "- `torch_accelerated` is the canonical accelerator lane and is currently CUDA-validated when a compatible PyTorch build is installed.",
            "- ROCm validation remains pending real AMD hardware access; a skipped accelerator row is not evidence of ROCm support.",
        ]
    )
    text = "\n".join(lines) + "\n"
    validate_report_text(text)
    return text


def build_fidelity_markdown(
    *,
    metadata: dict[str, object],
    fidelity_records: list[dict[str, object]],
) -> str:
    lines = [
        "# SRAM Analytical Fidelity Report",
        "",
        f"- Suite: `{metadata['suite']}`",
        f"- Device mode: `{metadata['device_mode']}`",
        f"- Seed: `{metadata['seed']}`",
        "",
        "| Pair | Status | Max Abs Delta | Mean Abs Delta | RMSE | Threshold Max | Threshold Mean |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    detail_lines: list[str] = []
    for record in fidelity_records:
        lines.append(
            "| "
            f"{normalize_fidelity_pair_name(str(record['pair']))} | {record['status']} | {float(record['max_abs_delta']):.6e} | "
            f"{float(record['mean_abs_delta']):.6e} | {float(record['rmse']):.6e} | "
            f"{float(record['threshold_max_abs_delta']):.6e} | {float(record['threshold_mean_abs_delta']):.6e} |"
        )
        if record.get("detail"):
            detail_lines.append(f"- {normalize_fidelity_pair_name(str(record['pair']))}: {record['detail']}")
    if detail_lines:
        lines.extend(["", "## Details", ""])
        lines.extend(detail_lines)
    text = "\n".join(lines) + "\n"
    validate_report_text(text)
    return text


def write_markdown(path: Path, text: str) -> None:
    validate_report_text(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_optional_plots(artifact_dir: Path, rows: Iterable[dict[str, object]]) -> list[str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return []

    row_list = list(rows)
    passed_rows = [row for row in row_list if str(row.get("status", "")) == "pass"]
    if not passed_rows:
        return []

    artifact_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = artifact_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    lane_labels = [str(row["lane"]) for row in passed_rows]
    throughput_values = [float(row["throughput_samples_per_sec"]) for row in passed_rows]
    latency_values = [float(row["wall_clock_sec"]) for row in passed_rows]

    throughput_path = plots_dir / "throughput.png"
    plt.figure(figsize=(7, 4))
    plt.bar(lane_labels, throughput_values)
    plt.ylabel("samples / second")
    plt.title("Analytical Benchmark Throughput")
    plt.tight_layout()
    plt.savefig(str(throughput_path))
    plt.close()

    latency_path = plots_dir / "latency.png"
    plt.figure(figsize=(7, 4))
    plt.bar(lane_labels, latency_values)
    plt.ylabel("seconds")
    plt.title("Analytical Benchmark Median Wall Clock")
    plt.tight_layout()
    plt.savefig(str(latency_path))
    plt.close()

    return [
        "plots/throughput.png",
        "plots/latency.png",
    ]
