"""Analytical benchmark suite runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backends import accelerator_lane, cpu_existing, cpu_numpy
from backends.registry import LANE_ORDER, get_accelerator_backend_capability
from benchmarks.cases import BenchmarkCase, get_suite_cases, parse_cases
from benchmarks.env import collect_env_metadata
from benchmarks.metrics import compare_predictions, summarize_elapsed, summarize_predictions
from benchmarks.reports import (
    build_fidelity_markdown,
    build_report_markdown,
    write_json,
    write_markdown,
    write_optional_plots,
    write_results_csv,
)
from benchmarks.schema import validate_fidelity_records, validate_metadata, validate_report_text, validate_result_rows
from execution_policy import select_engine


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "benchmarks"
DEFAULT_FIDELITY_THRESHOLDS: dict[str, dict[str, float]] = {
    "cpu_existing_vs_cpu_numpy": {
        "max_abs_delta": 1e-6,
        "mean_abs_delta": 1e-7,
    },
    "cpu_existing_vs_torch_accelerated": {
        "max_abs_delta": 1e-3,
        "mean_abs_delta": 1e-4,
    },
}


@dataclass
class SuiteResult:
    artifact_dir: Path
    metadata: dict[str, Any]
    rows: list[dict[str, object]]
    fidelity_records: list[dict[str, object]]
    report_text: str
    fidelity_text: str


def _suite_training_shape(suite: str) -> tuple[int, int]:
    return (1024, 64) if str(suite).strip().lower() == "smoke" else (4096, 256)


def _suite_execution_shape(suite: str) -> tuple[int, int]:
    return (0, 1) if str(suite).strip().lower() == "smoke" else (1, 3)


def _suite_training_iterations(suite: str) -> int:
    return 300 if str(suite).strip().lower() == "smoke" else 4000


def _status_for_capability(reason: str) -> str:
    if reason in {"torch-unavailable", "accelerator-unavailable", "device_mode_cpu", "forced_cpu_env"}:
        return "skipped"
    return "unsupported"


def _resolve_validation_scope(rows: list[dict[str, object]]) -> str:
    accelerated_rows = [
        row
        for row in rows
        if str(row.get("lane", "")) == "torch_accelerated" and str(row.get("status", "")) == "pass"
    ]
    if not accelerated_rows:
        return "cpu_validated"
    if any(str(row.get("backend_kind", "")) == "hip" for row in accelerated_rows):
        return "rocm_validated"
    if any(str(row.get("backend_kind", "")) == "cuda" for row in accelerated_rows):
        return "cuda_validated"
    return "accelerator_validated"


def _run_lane(
    *,
    lane: str,
    case: BenchmarkCase,
    seed: int,
    latency_mode: str,
    device_mode: str,
    warmup_runs: int,
    repeat_runs: int,
    model: object,
    exported_gpu_model: object | None,
) -> dict[str, object]:
    compute_mode = "gpu" if lane == "torch_accelerated" and device_mode != "cpu" else "cpu"
    selected_engine, selection_reason, work_size, gpu_detected = select_engine(
        "analytical_dataset",
        {
            "n_samples": case.n_samples,
            "variability_samples": case.variability_samples,
            "compute_mode": compute_mode,
            "latency_mode": latency_mode,
        },
    )

    if lane == "cpu_existing":
        run_callable = cpu_existing.run_case
        runner_arg = model
        lane_capability = cpu_existing.capability()
    elif lane == "cpu_numpy":
        run_callable = cpu_numpy.run_case
        runner_arg = model
        lane_capability = cpu_numpy.capability()
    else:
        lane_capability = get_accelerator_backend_capability(device_mode=device_mode)
        if not lane_capability.available or exported_gpu_model is None:
            return {
                "case_id": case.case_id,
                "lane": lane,
                "status": _status_for_capability(lane_capability.reason),
                "selected_engine": selected_engine,
                "selection_reason": selection_reason,
                "backend_reason": lane_capability.reason,
                "work_size": work_size,
                "gpu_detected": bool(gpu_detected),
                "device_name": lane_capability.device_display_name or lane_capability.reason,
                "device_display_name": lane_capability.device_display_name or lane_capability.reason,
                "backend_kind": lane_capability.backend_kind,
                "runtime_kind": lane_capability.runtime_kind,
                "wall_clock_sec": 0.0,
                "wall_clock_sec_mean": 0.0,
                "wall_clock_sec_std": 0.0,
                "wall_clock_sec_p95": 0.0,
                "throughput_samples_per_sec": 0.0,
                "mean_prediction": 0.0,
                "std_prediction": 0.0,
                "repeat_runs": int(repeat_runs),
                "warmup_runs": int(warmup_runs),
            }
        run_callable = accelerator_lane.run_case
        runner_arg = exported_gpu_model
    capability_reason = lane_capability.reason

    for warmup_index in range(max(int(warmup_runs), 0)):
        run_callable(
            runner_arg,
            n_samples=case.n_samples,
            variability_samples=case.variability_samples,
            seed=int(seed) + warmup_index,
        )

    elapsed_values: list[float] = []
    predictions = None
    device_name = "cpu"
    for repeat_index in range(max(int(repeat_runs), 1)):
        output = run_callable(
            runner_arg,
            n_samples=case.n_samples,
            variability_samples=case.variability_samples,
            seed=int(seed) + 100 + repeat_index,
        )
        elapsed_values.append(float(output.elapsed_sec))
        predictions = output.predictions
        device_name = str(output.device_name)

    row = {
        "case_id": case.case_id,
        "lane": lane,
        "status": "pass",
        "selected_engine": selected_engine,
        "selection_reason": selection_reason,
        "backend_reason": capability_reason,
        "work_size": work_size,
        "gpu_detected": bool(gpu_detected),
        "device_name": device_name,
        "device_display_name": str(getattr(output, "device_display_name", "")) or device_name,
        "backend_kind": str(getattr(output, "backend_kind", lane_capability.backend_kind)),
        "runtime_kind": str(getattr(output, "runtime_kind", lane_capability.runtime_kind)),
        "repeat_runs": int(repeat_runs),
        "warmup_runs": int(warmup_runs),
    }
    row.update(summarize_elapsed(elapsed_values, case.n_samples))
    row.update(summarize_predictions(predictions))
    return row


def _build_fidelity_records(
    *,
    suite: str,
    seed: int,
    device_mode: str,
    model: object,
    exported_gpu_model: object | None,
) -> list[dict[str, object]]:
    eval_dataset = cpu_numpy.build_chunked_numpy_dataset(
        n_samples=512 if str(suite).strip().lower() == "smoke" else 2048,
        variability_samples=64,
        seed=int(seed),
    )
    x = eval_dataset["X"]
    reference = cpu_existing.predict_on_features(model, x)
    numpy_pred = cpu_numpy.perceptron_predict_numpy(model, x)

    cpu_numpy_delta = compare_predictions(reference, numpy_pred)
    cpu_numpy_threshold = DEFAULT_FIDELITY_THRESHOLDS["cpu_existing_vs_cpu_numpy"]
    records = [
        {
            "pair": "cpu_existing_vs_cpu_numpy",
            "status": (
                "pass"
                if cpu_numpy_delta["max_abs_delta"] <= cpu_numpy_threshold["max_abs_delta"]
                and cpu_numpy_delta["mean_abs_delta"] <= cpu_numpy_threshold["mean_abs_delta"]
                else "fail"
            ),
            "threshold_max_abs_delta": cpu_numpy_threshold["max_abs_delta"],
            "threshold_mean_abs_delta": cpu_numpy_threshold["mean_abs_delta"],
            "max_abs_delta": cpu_numpy_delta["max_abs_delta"],
            "mean_abs_delta": cpu_numpy_delta["mean_abs_delta"],
            "rmse": cpu_numpy_delta["rmse"],
            "detail": "Common CPU feature matrix with NumPy/manual-forward parity check.",
        }
    ]

    gpu_cap = get_accelerator_backend_capability(device_mode=device_mode)
    gpu_threshold = DEFAULT_FIDELITY_THRESHOLDS["cpu_existing_vs_torch_accelerated"]
    if exported_gpu_model is not None and gpu_cap.available:
        gpu_pred = accelerator_lane.predict_on_features(exported_gpu_model, x)
        gpu_delta = compare_predictions(reference, gpu_pred)
        records.append(
            {
                "pair": "cpu_existing_vs_torch_accelerated",
                "status": (
                    "pass"
                    if gpu_delta["max_abs_delta"] <= gpu_threshold["max_abs_delta"]
                    and gpu_delta["mean_abs_delta"] <= gpu_threshold["mean_abs_delta"]
                    else "fail"
                ),
                "threshold_max_abs_delta": gpu_threshold["max_abs_delta"],
                "threshold_mean_abs_delta": gpu_threshold["mean_abs_delta"],
                "max_abs_delta": gpu_delta["max_abs_delta"],
                "mean_abs_delta": gpu_delta["mean_abs_delta"],
                "rmse": gpu_delta["rmse"],
                "detail": "Common CPU feature matrix with the canonical torch_accelerated lane.",
            }
        )
    else:
        records.append(
            {
                "pair": "cpu_existing_vs_torch_accelerated",
                "status": _status_for_capability(gpu_cap.reason),
                "threshold_max_abs_delta": gpu_threshold["max_abs_delta"],
                "threshold_mean_abs_delta": gpu_threshold["mean_abs_delta"],
                "max_abs_delta": 0.0,
                "mean_abs_delta": 0.0,
                "rmse": 0.0,
                "detail": f"Accelerator fidelity skipped: {gpu_cap.reason}.",
            }
        )
    return records


def _artifact_dir(artifact_root: Path, suite: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return artifact_root / f"{timestamp}_{suite}"


def run_suite(
    *,
    suite: str = "smoke",
    device_mode: str = "auto",
    artifact_root: Path | None = None,
    seed: int = 20260310,
    latency_mode: str = "batch",
    cases: list[BenchmarkCase] | None = None,
    case_text: str | None = None,
    warmup_runs: int | None = None,
    repeat_runs: int | None = None,
) -> SuiteResult:
    suite_key = str(suite).strip().lower() or "smoke"
    resolved_cases = cases
    if resolved_cases is None:
        resolved_cases = parse_cases(case_text) if case_text else get_suite_cases(suite_key)

    default_warmup, default_repeat = _suite_execution_shape(suite_key)
    warmup = default_warmup if warmup_runs is None else int(warmup_runs)
    repeats = default_repeat if repeat_runs is None else int(repeat_runs)

    train_samples, train_variability = _suite_training_shape(suite_key)
    model = cpu_existing.fit_reference_perceptron(
        n_samples=train_samples,
        variability_samples=train_variability,
        seed=int(seed),
        max_iter=_suite_training_iterations(suite_key),
    )

    gpu_capability = get_accelerator_backend_capability(device_mode=device_mode)
    exported_gpu_model = accelerator_lane.export_model(model) if gpu_capability.available else None

    rows = [
        _run_lane(
            lane=lane,
            case=case,
            seed=int(seed) + case_index * 1000,
            latency_mode=latency_mode,
            device_mode=device_mode,
            warmup_runs=warmup,
            repeat_runs=repeats,
            model=model,
            exported_gpu_model=exported_gpu_model,
        )
        for case_index, case in enumerate(resolved_cases, start=1)
        for lane in LANE_ORDER
    ]

    fidelity_records = _build_fidelity_records(
        suite=suite_key,
        seed=int(seed),
        device_mode=device_mode,
        model=model,
        exported_gpu_model=exported_gpu_model,
    )

    env = collect_env_metadata(device_mode=device_mode)
    validation_scope = _resolve_validation_scope(rows)
    metadata: dict[str, Any] = {
        "suite": suite_key,
        "device_mode": device_mode,
        "seed": int(seed),
        "latency_mode": latency_mode,
        "warmup_runs": int(warmup),
        "repeat_runs": int(repeats),
        "cases": [asdict(case) for case in resolved_cases],
        "validation_scope": validation_scope,
        "claim_level": "measured",
        "backend_capabilities": env.pop("backend_capabilities"),
        "env": env,
        "artifact_files": ["metadata.json", "results.csv", "report.md", "fidelity.md"],
    }

    validate_metadata(metadata)
    validate_result_rows(rows)
    validate_fidelity_records(fidelity_records)

    artifact_base = DEFAULT_ARTIFACT_ROOT if artifact_root is None else Path(artifact_root)
    artifact_dir = _artifact_dir(artifact_base, suite_key)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    report_text = build_report_markdown(metadata=metadata, rows=rows, fidelity_records=fidelity_records)
    fidelity_text = build_fidelity_markdown(metadata=metadata, fidelity_records=fidelity_records)
    validate_report_text(report_text)
    validate_report_text(fidelity_text)

    write_results_csv(artifact_dir / "results.csv", rows)
    write_markdown(artifact_dir / "report.md", report_text)
    write_markdown(artifact_dir / "fidelity.md", fidelity_text)
    plot_files = write_optional_plots(artifact_dir, rows)
    if plot_files:
        metadata["artifact_files"] = list(metadata["artifact_files"]) + list(plot_files)
    write_json(artifact_dir / "metadata.json", metadata)

    return SuiteResult(
        artifact_dir=artifact_dir,
        metadata=metadata,
        rows=rows,
        fidelity_records=fidelity_records,
        report_text=report_text,
        fidelity_text=fidelity_text,
    )
