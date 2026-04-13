"""Benchmark analytical dataset generation + surrogate inference lanes."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from execution_policy import select_engine


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float) -> str:
    return f"{float(value):.6f}"


def run_cpu_existing_case(model, *, n_samples: int, variability_samples: int, seed: int) -> tuple[float, np.ndarray]:
    from gpu_analytical_adapter import build_numpy_dataset

    started = time.perf_counter()
    dataset = build_numpy_dataset(
        n_samples=n_samples,
        variability_samples=variability_samples,
        seed=seed,
    )
    predictions = model.predict(dataset["X"])
    elapsed = time.perf_counter() - started
    return elapsed, np.asarray(predictions, dtype=float)


def run_cpu_numpy_case(model, *, n_samples: int, variability_samples: int, seed: int) -> tuple[float, np.ndarray]:
    from gpu_analytical_adapter import build_chunked_numpy_dataset, perceptron_predict_numpy

    started = time.perf_counter()
    dataset = build_chunked_numpy_dataset(
        n_samples=n_samples,
        variability_samples=variability_samples,
        seed=seed,
    )
    predictions = perceptron_predict_numpy(model, dataset["X"])
    elapsed = time.perf_counter() - started
    return elapsed, np.asarray(predictions, dtype=float)


def run_gpu_torch_case(exported_model, *, n_samples: int, variability_samples: int, seed: int) -> tuple[float, np.ndarray]:
    from gpu_analytical_adapter import build_torch_dataset, perceptron_predict_torch, torch

    started = time.perf_counter()
    dataset = build_torch_dataset(
        n_samples=n_samples,
        variability_samples=variability_samples,
        seed=seed,
        device=exported_model.device,
    )
    predictions = perceptron_predict_torch(exported_model, dataset["X"])
    if torch is None:
        raise RuntimeError("PyTorch is unavailable")
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    return elapsed, predictions.detach().cpu().numpy()


def write_report(
    path: Path,
    rows: list[dict[str, object]],
    *,
    smoke_max_abs_delta: float,
    smoke_mean_abs_delta: float,
    cuda_status: str,
) -> None:
    lines: list[str] = [
        "# GPU Analytical Benchmark",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- CUDA status: `{cuda_status}`",
        f"- Smoke max abs prediction delta: `{smoke_max_abs_delta:.6e}`",
        f"- Smoke mean abs prediction delta: `{smoke_mean_abs_delta:.6e}`",
        "",
        "## Benchmark Results",
        "",
        "| Case | Lane | Status | Selected Engine | Device | Wall Clock (s) | Throughput (samples/s) | Mean Prediction |",
        "|---|---|---|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['case_id']} | {row['lane']} | {row['status']} | {row['selected_engine']} | {row['device_name']} | "
            f"{float(row['wall_clock_sec']):.6f} | {float(row['throughput_samples_per_sec']):.3f} | "
            f"{float(row['mean_prediction']):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `CPU existing` uses `AnalyticalSRAMModel.generate_dataset()` and the fitted perceptron `.predict()` path.",
            "- `CPU NumPy` uses chunked analytical generation plus manual NumPy forward on exported perceptron weights.",
            "- `GPU PyTorch` is limited to analytical dataset generation plus batched perceptron inference.",
            "- GPU rows are marked `skipped` when PyTorch or CUDA is unavailable.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run analytical dataset GPU benchmark")
    parser.add_argument("--cases", default="10000x512,5000x1024,20000x512")
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument("--latency-mode", default="batch")
    parser.add_argument("--out-csv", type=Path, default=REPO_ROOT / "reports" / "gpu_analytical_benchmark.csv")
    parser.add_argument("--out-report", type=Path, default=REPO_ROOT / "reports" / "gpu_analytical_benchmark.md")
    args = parser.parse_args()

    from gpu_analytical_adapter import (
        build_chunked_numpy_dataset,
        export_perceptron_to_torch,
        fit_reference_perceptron,
        perceptron_predict_numpy,
        perceptron_predict_torch,
        torch,
        torch_cuda_info,
    )

    case_specs: list[tuple[int, int]] = []
    for token in str(args.cases).split(","):
        token = token.strip()
        if not token:
            continue
        left, right = token.lower().split("x", 1)
        case_specs.append((int(left), int(right)))
    if not case_specs:
        raise ValueError("at least one case is required")

    model = fit_reference_perceptron(seed=int(args.seed))
    cuda_available, cuda_status = torch_cuda_info()
    exported_model = export_perceptron_to_torch(model) if cuda_available else None

    smoke_max_abs_delta = float("nan")
    smoke_mean_abs_delta = float("nan")
    if exported_model is not None and torch is not None:
        smoke_dataset = build_chunked_numpy_dataset(n_samples=512, variability_samples=64, seed=int(args.seed))
        cpu_pred = perceptron_predict_numpy(model, smoke_dataset["X"])
        x_tensor = torch.tensor(smoke_dataset["X"], dtype=torch.float32, device=exported_model.device)
        gpu_pred = perceptron_predict_torch(exported_model, x_tensor).detach().cpu().numpy()
        smoke_delta = np.abs(cpu_pred - gpu_pred)
        smoke_max_abs_delta = float(np.max(smoke_delta))
        smoke_mean_abs_delta = float(np.mean(smoke_delta))

    rows: list[dict[str, object]] = []
    for case_index, (n_samples, variability_samples) in enumerate(case_specs, start=1):
        case_id = f"{n_samples}x{variability_samples}"
        for lane in ("cpu_existing", "cpu_numpy", "gpu_pytorch"):
            compute_mode = "gpu" if lane == "gpu_pytorch" else "cpu"
            selected_engine, reason, work_size, gpu_detected = select_engine(
                "analytical_dataset",
                {
                    "n_samples": n_samples,
                    "variability_samples": variability_samples,
                    "compute_mode": compute_mode,
                    "latency_mode": args.latency_mode,
                },
            )
            device_name = "cpu"
            status = "pass"
            wall_clock_sec = 0.0
            predictions = np.asarray([], dtype=float)
            if lane == "cpu_existing":
                wall_clock_sec, predictions = run_cpu_existing_case(
                    model,
                    n_samples=n_samples,
                    variability_samples=variability_samples,
                    seed=int(args.seed) + case_index,
                )
            elif lane == "cpu_numpy":
                wall_clock_sec, predictions = run_cpu_numpy_case(
                    model,
                    n_samples=n_samples,
                    variability_samples=variability_samples,
                    seed=int(args.seed) + case_index,
                )
            else:
                if exported_model is None:
                    status = "skipped"
                    device_name = cuda_status
                else:
                    device_name = cuda_status
                    wall_clock_sec, predictions = run_gpu_torch_case(
                        exported_model,
                        n_samples=n_samples,
                        variability_samples=variability_samples,
                        seed=int(args.seed) + case_index,
                    )

            throughput = (n_samples / wall_clock_sec) if wall_clock_sec > 0.0 else 0.0
            rows.append(
                {
                    "case_id": case_id,
                    "lane": lane,
                    "status": status,
                    "selected_engine": selected_engine,
                    "selection_reason": reason,
                    "work_size": work_size,
                    "gpu_detected": bool(gpu_detected),
                    "device_name": device_name,
                    "wall_clock_sec": float(wall_clock_sec),
                    "throughput_samples_per_sec": float(throughput),
                    "mean_prediction": float(np.mean(predictions)) if predictions.size else 0.0,
                }
            )

    write_csv(args.out_csv, rows)
    write_report(
        args.out_report,
        rows,
        smoke_max_abs_delta=smoke_max_abs_delta if np.isfinite(smoke_max_abs_delta) else 0.0,
        smoke_mean_abs_delta=smoke_mean_abs_delta if np.isfinite(smoke_mean_abs_delta) else 0.0,
        cuda_status=cuda_status,
    )
    print(f"[ok] wrote csv: {args.out_csv}")
    print(f"[ok] wrote report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
