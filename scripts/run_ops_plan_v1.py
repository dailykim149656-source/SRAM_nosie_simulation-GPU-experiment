"""Ops Plan v1 orchestration entrypoint."""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_manifest(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return loaded


def write_summary(path: Path, rows: list[dict[str, object]], tag: str) -> None:
    lines = [
        "# Ops Plan v1 Summary",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Tag: `{tag}`",
        "",
        "| Step | Status | Output |",
        "|---|---|---|",
    ]
    for row in rows:
        output = str(row.get("output", "")).replace("\\", "/")
        lines.append(f"| {row['step']} | {row['status']} | `{output}` |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_docs_pointer(path: Path, tag: str, out_root: Path) -> None:
    lines = [
        "# Ops Plan v1 Latest",
        "",
        f"- Latest tag: `{tag}`",
        f"- Summary: `{(out_root / 'ops_plan_v1_summary.md').as_posix()}`",
        f"- Gate B summary: `{(out_root / 'gate_b' / 'gate_b_summary.md').as_posix()}`",
        f"- Parallel benchmark: `{(out_root / 'parallel' / 'matrix_parallel_benchmark.md').as_posix()}`",
        f"- Node scaling: `{(out_root / 'node_scaling' / 'node_scaling_report.md').as_posix()}`",
        f"- Evidence pack: `{(out_root / 'research_evidence_pack.md').as_posix()}`",
        "",
        "This file is a pointer document for the latest Ops Plan v1 run artifacts kept under `reports/ops_plan_v1/<tag>/`.",
        "Claim boundary remains `pre-signoff acceleration`.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_command(
    *,
    step_name: str,
    cmd: list[str],
    log_path: Path,
    continue_on_error: bool,
) -> dict[str, object]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    log_path.write_text(
        f"$ {' '.join(cmd)}\n\n[stdout]\n{completed.stdout}\n\n[stderr]\n{completed.stderr}",
        encoding="utf-8",
    )
    status = "pass" if completed.returncode == 0 else "fail"
    if completed.returncode != 0 and not continue_on_error:
        raise RuntimeError(f"{step_name} failed with exit code {completed.returncode}. See {log_path}")
    return {"step": step_name, "status": status, "log": str(log_path), "return_code": completed.returncode}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ops Plan v1 orchestration")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "configs" / "ops_plan_v1.json")
    parser.add_argument("--tag", default="ops_plan_v1")
    parser.add_argument("--python-bin", type=Path, default=Path(sys.executable))
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--allow-contract-fallback", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    out_root = REPO_ROOT / "reports" / "ops_plan_v1" / str(args.tag)
    logs_dir = out_root / "logs"
    results: list[dict[str, object]] = []

    preflight_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "check_ops_plan_v1_env.py"),
        "--manifest",
        str(args.manifest),
        "--out-json",
        str(out_root / "ops_plan_v1_env_check.json"),
    ]
    results.append(
        {
            **run_command(
                step_name="env_preflight",
                cmd=preflight_cmd,
                log_path=logs_dir / "00_env_preflight.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": out_root / "ops_plan_v1_env_check.json",
        }
    )

    runnable_subset = [str(v) for v in manifest.get("runnable_pdk_subset", [])]
    pdk_run_configs = manifest.get("pdk_run_configs", {})
    if pdk_run_configs is None:
        pdk_run_configs = {}
    if not isinstance(pdk_run_configs, dict):
        raise ValueError("pdk_run_configs must be an object when provided")
    model_selection = manifest.get("model_selection", {})
    if not isinstance(model_selection, dict):
        raise ValueError("model_selection section missing from manifest")
    baseline = model_selection.get("baseline", {})
    if not isinstance(baseline, dict):
        raise ValueError("model_selection.baseline section missing from manifest")

    gate_b_dir = out_root / "gate_b"
    gate_b_tag = f"{args.tag}_gate_b_repro"
    gate_b_summary_csv = gate_b_dir / "pdk_matrix_summary.csv"
    gate_b_summary_report = gate_b_dir / "pdk_matrix_summary.md"
    gate_b_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "run_pdk_matrix.py"),
        "--python-bin",
        str(args.python_bin),
        "--pdk-ids",
        ",".join(runnable_subset),
        "--tag",
        gate_b_tag,
        "--max-workers",
        "1",
        "--summary-csv",
        str(gate_b_summary_csv),
        "--summary-report",
        str(gate_b_summary_report),
        "--out-root",
        str(gate_b_dir),
    ]
    for pdk_id, config_path in pdk_run_configs.items():
        gate_b_cmd.extend(["--config-override", f"{pdk_id}={config_path}"])
    if args.allow_contract_fallback:
        gate_b_cmd.append("--allow-contract-fallback")
    results.append(
        {
            **run_command(
                step_name="gate_b_reproduction",
                cmd=gate_b_cmd,
                log_path=logs_dir / "01_gate_b_reproduction.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": gate_b_summary_report,
        }
    )

    audit_cmd = [str(args.python_bin), str(REPO_ROOT / "scripts" / "run_raw_metric_audit.py"), "--tag", str(args.tag), "--out-report", str(out_root / "raw_metric_audit.md"), "--out-csv", str(out_root / "raw_metric_audit.csv")]
    for pdk_id in runnable_subset:
        audit_cmd.extend(["--csv-path", str(gate_b_dir / "results" / f"spice_vs_native_pdk_{pdk_id}_{gate_b_tag}.csv")])
    results.append(
        {
            **run_command(
                step_name="raw_metric_audit",
                cmd=audit_cmd,
                log_path=logs_dir / "02_raw_metric_audit.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": out_root / "raw_metric_audit.md",
        }
    )

    baseline_args = [
        "--target-source",
        str(baseline.get("target_source", "spice_v2")),
        "--risk-weighting",
        "true" if bool(baseline.get("risk_weighting", True)) else "false",
        "--split-mode",
        str(baseline.get("split_mode", "group_pvt")),
        "--target-prob-logit",
        "true" if bool(baseline.get("target_prob_logit", True)) else "false",
        "--target-normalize",
        "true" if bool(baseline.get("target_normalize", True)) else "false",
        "--fail-aux-split",
        "true" if bool(baseline.get("fail_aux_split", False)) else "false",
        "--fail-aux-profile",
        str(baseline.get("fail_aux_profile", "auto")),
        "--n-folds",
        str(int(baseline.get("n_folds", 5))),
        "--random-state",
        str(int(manifest.get("seeds", {}).get("model_selection_random_state", 42) if isinstance(manifest.get("seeds"), dict) else 42)),
    ]

    for index, pdk_id in enumerate(runnable_subset, start=1):
        input_csv = gate_b_dir / "results" / f"spice_vs_native_pdk_{pdk_id}_{gate_b_tag}.csv"
        output_dir = out_root / "model_selection" / "baseline" / pdk_id
        cmd = [
            str(args.python_bin),
            str(REPO_ROOT / "scripts" / "run_model_selection.py"),
            "--input-csv",
            str(input_csv),
            "--data-source",
            "foundry-pdk-pre-silicon" if pdk_id in {"sky130", "gf180mcu"} else "predictive-pdk-pre-silicon",
            "--pareto-csv",
            str(output_dir / "model_pareto.csv"),
            "--report-path",
            str(output_dir / "model_selection_report.md"),
            *baseline_args,
        ]
        results.append(
            {
                **run_command(
                    step_name=f"model_selection_baseline_{pdk_id}",
                    cmd=cmd,
                    log_path=logs_dir / f"03_{index:02d}_model_selection_baseline_{pdk_id}.log",
                    continue_on_error=bool(args.continue_on_error),
                ),
                "output": output_dir / "model_selection_report.md",
            }
        )

    gate_b_summary_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "build_gate_b_summary.py"),
        "--results-dir",
        str(gate_b_dir / "results"),
        "--baseline-dir",
        str(out_root / "model_selection" / "baseline"),
        "--report-glob",
        str(gate_b_dir / "reports" / "spice_correlation_pdk_*.md"),
        "--out-csv",
        str(out_root / "gate_b" / "gate_b_summary.csv"),
        "--out-report",
        str(out_root / "gate_b" / "gate_b_summary.md"),
    ]
    thresholds = manifest.get("gate_b_thresholds", {})
    if isinstance(thresholds, dict):
        gate_b_summary_cmd.extend(["--snm-mae-mv-max", str(float(thresholds.get("snm_mae_mv_max", 10.0)))])
        gate_b_summary_cmd.extend(["--noise-sigma-mae-max", str(float(thresholds.get("noise_sigma_mae_max", 0.02)))])
        gate_b_summary_cmd.extend(["--log10-ber-mae-max", str(float(thresholds.get("log10_ber_mae_max", 0.35)))])
        gate_b_summary_cmd.extend(["--max-abs-ber-delta-max", str(float(thresholds.get("max_abs_ber_delta_max", 0.05)))])
        gate_b_summary_cmd.extend(["--latency-gain-min", str(float(thresholds.get("latency_gain_min", 50.0)))])
    results.append(
        {
            **run_command(
                step_name="gate_b_summary",
                cmd=gate_b_summary_cmd,
                log_path=logs_dir / "03_gate_b_summary.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": out_root / "gate_b" / "gate_b_summary.md",
        }
    )

    ablation_pdks = [str(v) for v in model_selection.get("ablation_pdks", [])]
    ablation_grid = model_selection.get("ablation_grid", {})
    if not isinstance(ablation_grid, dict):
        raise ValueError("model_selection.ablation_grid must be an object")
    grid_values = [
        list(ablation_grid.get("split_mode", [])),
        list(ablation_grid.get("risk_weighting", [])),
        list(ablation_grid.get("target_source", [])),
        list(ablation_grid.get("target_prob_logit", [])),
    ]
    combinations = list(itertools.product(*grid_values))
    for pdk_id in ablation_pdks:
        input_csv = gate_b_dir / "results" / f"spice_vs_native_pdk_{pdk_id}_{gate_b_tag}.csv"
        for combo_index, (split_mode, risk_weighting, target_source, target_prob_logit) in enumerate(combinations, start=1):
            combo_tag = f"{pdk_id}_{target_source}_{split_mode}_rw{int(bool(risk_weighting))}_logit{int(bool(target_prob_logit))}"
            output_dir = out_root / "model_selection" / "ablation" / pdk_id / combo_tag
            cmd = [
                str(args.python_bin),
                str(REPO_ROOT / "scripts" / "run_model_selection.py"),
                "--input-csv",
                str(input_csv),
                "--target-source",
                str(target_source),
                "--risk-weighting",
                "true" if bool(risk_weighting) else "false",
                "--split-mode",
                str(split_mode),
                "--target-prob-logit",
                "true" if bool(target_prob_logit) else "false",
                "--target-normalize",
                "true",
                "--fail-aux-split",
                "false",
                "--fail-aux-profile",
                str(pdk_id),
                "--data-source",
                "foundry-pdk-pre-silicon" if pdk_id in {"sky130", "gf180mcu"} else "predictive-pdk-pre-silicon",
                "--pareto-csv",
                str(output_dir / "model_pareto.csv"),
                "--report-path",
                str(output_dir / "model_selection_report.md"),
                "--random-state",
                str(int(manifest.get("seeds", {}).get("model_selection_random_state", 42) if isinstance(manifest.get("seeds"), dict) else 42)),
            ]
            results.append(
                {
                    **run_command(
                        step_name=f"model_selection_ablation_{combo_tag}",
                        cmd=cmd,
                        log_path=logs_dir / f"04_{pdk_id}_{combo_index:02d}_ablation.log",
                        continue_on_error=bool(args.continue_on_error),
                    ),
                    "output": output_dir / "model_selection_report.md",
                }
            )

    fidelity_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "native_hybrid_fidelity_check.py"),
    ]
    results.append(
        {
            **run_command(
                step_name="native_hybrid_fidelity",
                cmd=fidelity_cmd,
                log_path=logs_dir / "05_native_hybrid_fidelity.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": logs_dir / "05_native_hybrid_fidelity.log",
        }
    )

    gpu_cases = manifest.get("gpu_benchmark", {}).get("batch_shapes", []) if isinstance(manifest.get("gpu_benchmark"), dict) else []
    case_text = ",".join(f"{int(item['n_samples'])}x{int(item['variability_samples'])}" for item in gpu_cases if isinstance(item, dict))
    gpu_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "run_gpu_analytical_benchmark.py"),
        "--cases",
        case_text or "10000x512,5000x1024,20000x512",
        "--seed",
        str(int(manifest.get("seeds", {}).get("gpu_benchmark_seed", 20260310) if isinstance(manifest.get("seeds"), dict) else 20260310)),
        "--out-csv",
        str(out_root / "gpu" / "gpu_analytical_benchmark.csv"),
        "--out-report",
        str(out_root / "gpu" / "gpu_analytical_benchmark.md"),
    ]
    results.append(
        {
            **run_command(
                step_name="gpu_analytical_benchmark",
                cmd=gpu_cmd,
                log_path=logs_dir / "06_gpu_analytical_benchmark.log",
                continue_on_error=True,
            ),
            "output": out_root / "gpu" / "gpu_analytical_benchmark.md",
        }
    )

    parallel_cfg = manifest.get("parallel_benchmark", {})
    if not isinstance(parallel_cfg, dict):
        raise ValueError("parallel_benchmark section missing from manifest")
    parallel_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "run_matrix_parallel_benchmark.py"),
        "--pdk-ids",
        ",".join(str(v) for v in parallel_cfg.get("pdk_ids", ["gf180mcu", "freepdk45_openram"])),
        "--blocked-pdks",
        ",".join(str(v) for v in manifest.get("blocked_pdk_subset", ["ihp_sg13g2"])),
        "--worker-ladder",
        ",".join(str(v) for v in parallel_cfg.get("worker_ladder", [1, 2, 4, 8])),
        "--repeats",
        str(int(parallel_cfg.get("repeats", 2))),
        "--timeout-sec",
        str(int(parallel_cfg.get("timeout_sec", 1800))),
        "--out-root",
        str(out_root / "parallel"),
        "--out-csv",
        str(out_root / "parallel" / "matrix_parallel_benchmark.csv"),
        "--out-report",
        str(out_root / "parallel" / "matrix_parallel_benchmark.md"),
    ]
    for pdk_id, config_path in pdk_run_configs.items():
        if str(pdk_id) in {str(v) for v in parallel_cfg.get("pdk_ids", [])}:
            parallel_cmd.extend(["--config-override", f"{pdk_id}={config_path}"])
    if args.allow_contract_fallback:
        parallel_cmd.append("--allow-contract-fallback")
    results.append(
        {
            **run_command(
                step_name="matrix_parallel_benchmark",
                cmd=parallel_cmd,
                log_path=logs_dir / "07_matrix_parallel_benchmark.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": out_root / "parallel" / "matrix_parallel_benchmark.md",
        }
    )

    node_cfg = manifest.get("node_scaling", {})
    if not isinstance(node_cfg, dict):
        raise ValueError("node_scaling section missing from manifest")
    node_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "run_node_scaling.py"),
        "--workload",
        str(node_cfg.get("workload", "llama_7b_online")),
        "--corners",
        ",".join(str(v) for v in node_cfg.get("corners", ["tt", "ff", "ss"])),
        "--temps-k",
        ",".join(str(v) for v in node_cfg.get("temps_k", [300, 330, 360])),
        "--vdds",
        str(node_cfg.get("vdds", "auto")),
        "--seed",
        str(int(manifest.get("seeds", {}).get("node_scaling_seed", 20260219) if isinstance(manifest.get("seeds"), dict) else 20260219)),
        "--out-csv",
        str(out_root / "node_scaling" / "node_tradeoff.csv"),
        "--out-report",
        str(out_root / "node_scaling" / "node_scaling_report.md"),
    ]
    results.append(
        {
            **run_command(
                step_name="node_scaling",
                cmd=node_cmd,
                log_path=logs_dir / "08_node_scaling.log",
                continue_on_error=True,
            ),
            "output": out_root / "node_scaling" / "node_scaling_report.md",
        }
    )

    summary_path = out_root / "ops_plan_v1_summary.md"
    write_summary(summary_path, results, str(args.tag))

    evidence_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "build_research_evidence_pack.py"),
        "--gate-b-report",
        str(out_root / "gate_b" / "gate_b_summary.md"),
        "--benchmark-report",
        str(out_root / "parallel" / "matrix_parallel_benchmark.md"),
        "--raw-audit-report",
        str(out_root / "raw_metric_audit.md"),
        "--model-selection-report",
        str(out_root / "model_selection" / "baseline" / runnable_subset[0] / "model_selection_report.md"),
        "--ops-plan-summary",
        str(summary_path),
        "--out-report",
        str(out_root / "research_evidence_pack.md"),
        "--tag",
        str(args.tag),
    ]
    results.append(
        {
            **run_command(
                step_name="research_evidence_pack",
                cmd=evidence_cmd,
                log_path=logs_dir / "09_research_evidence_pack.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": out_root / "research_evidence_pack.md",
        }
    )

    write_docs_pointer(REPO_ROOT / "docs" / "ops_plan_v1_latest.md", str(args.tag), out_root)

    verify_cmd = [
        str(args.python_bin),
        str(REPO_ROOT / "scripts" / "verify_ops_plan_v1_outputs.py"),
        "--manifest",
        str(args.manifest),
        "--root",
        str(out_root),
        "--out-json",
        str(out_root / "ops_plan_v1_verify.json"),
    ]
    results.append(
        {
            **run_command(
                step_name="final_verification",
                cmd=verify_cmd,
                log_path=logs_dir / "10_final_verification.log",
                continue_on_error=bool(args.continue_on_error),
            ),
            "output": out_root / "ops_plan_v1_verify.json",
        }
    )
    write_summary(summary_path, results, str(args.tag))

    print(f"[ok] wrote summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
