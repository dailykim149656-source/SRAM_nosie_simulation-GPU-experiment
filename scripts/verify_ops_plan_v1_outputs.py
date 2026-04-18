"""Verify Ops Plan v1 output completeness and key acceptance conditions."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.schema import CANONICAL_ACCELERATOR_LANE, normalize_lane_name


def load_manifest(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"manifest must be an object: {path}")
    return loaded


def parse_markdown_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        parts = [part.strip() for part in line.split("|")[1:-1]]
        if parts:
            rows.append(parts)
    return rows


def require_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        raise AssertionError(f"missing '{needle}' in {path}")


def validate_ops_plan_accelerator_rows(rows: list[dict[str, str]]) -> None:
    if len(rows) != 9:
        raise AssertionError(f"expected 9 gpu benchmark rows, found {len(rows)}")

    saw_accelerator_lane = False
    for row in rows:
        normalized_lane = normalize_lane_name(row["lane"])
        if normalized_lane != CANONICAL_ACCELERATOR_LANE:
            continue
        saw_accelerator_lane = True
        if row["status"] == "pass" and row["selected_engine"] != "gpu":
            raise AssertionError("accelerator row passed without gpu engine selection")

    if not saw_accelerator_lane:
        raise AssertionError(f"missing accelerator lane rows normalized to '{CANONICAL_ACCELERATOR_LANE}'")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Ops Plan v1 outputs")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "configs" / "ops_plan_v1.json")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    runnable_subset = [str(v) for v in manifest.get("runnable_pdk_subset", [])]
    ablation_pdks = [str(v) for v in manifest.get("model_selection", {}).get("ablation_pdks", [])] if isinstance(manifest.get("model_selection"), dict) else []
    ablation_grid = manifest.get("model_selection", {}).get("ablation_grid", {}) if isinstance(manifest.get("model_selection"), dict) else {}
    if not isinstance(ablation_grid, dict):
        ablation_grid = {}

    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    gate_b_summary = args.root / "gate_b" / "gate_b_summary.md"
    gate_b_csv = args.root / "gate_b" / "gate_b_summary.csv"
    if not gate_b_summary.exists() or not gate_b_csv.exists():
        raise FileNotFoundError("gate_b summary outputs missing")
    with gate_b_csv.open("r", encoding="utf-8", newline="") as fp:
        gate_rows = list(csv.DictReader(fp))
    gate_map = {str(row["pdk_id"]): row for row in gate_rows}
    for pdk_id in runnable_subset:
        row = gate_map.get(pdk_id)
        if row is None:
            raise AssertionError(f"missing Gate B row for {pdk_id}")
        if str(row["gate_b"]).strip().lower() != "pass":
            raise AssertionError(f"Gate B did not pass for {pdk_id}")
    record("gate_b_runnable_subset", True, f"{len(runnable_subset)}/{len(runnable_subset)} pass")

    raw_metric_audit = args.root / "raw_metric_audit.md"
    if not raw_metric_audit.exists():
        raise FileNotFoundError(raw_metric_audit)
    raw_text = raw_metric_audit.read_text(encoding="utf-8")
    for pdk_id, expected_source in {
        "sky130": "spice_read_snm_mv_raw",
        "freepdk45_openram": "spice_read_snm_mv_raw",
        "gf180mcu": "spice_snm_mv_raw",
        "asap7": "spice_snm_mv_raw",
    }.items():
        if pdk_id not in raw_text or expected_source not in raw_text:
            raise AssertionError(f"raw metric audit does not reflect expected source for {pdk_id}")
    record("raw_metric_contract_mapping", True, "expected primary source suggestions present")

    baseline_root = args.root / "model_selection" / "baseline"
    for pdk_id in runnable_subset:
        report_path = baseline_root / pdk_id / "model_selection_report.md"
        pareto_path = baseline_root / pdk_id / "model_pareto.csv"
        if not report_path.exists() or not pareto_path.exists():
            raise FileNotFoundError(f"baseline outputs missing for {pdk_id}")
        for needle in ("## Bootstrap CI", "## Worst-Corner Bias", "## OOD Guardrails", "Deployment candidate", "Accuracy ceiling"):
            require_contains(report_path, needle)
    record("model_selection_baselines", True, f"{len(runnable_subset)} baseline reports verified")

    expected_ablation_count = (
        len(ablation_pdks)
        * len(list(ablation_grid.get("split_mode", [])))
        * len(list(ablation_grid.get("risk_weighting", [])))
        * len(list(ablation_grid.get("target_source", [])))
        * len(list(ablation_grid.get("target_prob_logit", [])))
    )
    actual_ablation_reports = list((args.root / "model_selection" / "ablation").glob("*/*/model_selection_report.md"))
    if len(actual_ablation_reports) != expected_ablation_count:
        raise AssertionError(f"expected {expected_ablation_count} ablation reports, found {len(actual_ablation_reports)}")
    record("model_selection_ablations", True, f"{len(actual_ablation_reports)} reports")

    gpu_report = args.root / "gpu" / "gpu_analytical_benchmark.md"
    gpu_csv = args.root / "gpu" / "gpu_analytical_benchmark.csv"
    if not gpu_report.exists() or not gpu_csv.exists():
        raise FileNotFoundError("accelerator benchmark outputs missing")
    with gpu_csv.open("r", encoding="utf-8", newline="") as fp:
        gpu_rows = list(csv.DictReader(fp))
    validate_ops_plan_accelerator_rows(gpu_rows)
    record("gpu_benchmark", True, f"{len(gpu_rows)} benchmark rows verified with accelerator-lane normalization")

    parallel_report = args.root / "parallel" / "matrix_parallel_benchmark.md"
    parallel_csv = args.root / "parallel" / "matrix_parallel_benchmark.csv"
    if not parallel_report.exists() or not parallel_csv.exists():
        raise FileNotFoundError("parallel benchmark outputs missing")
    parallel_text = parallel_report.read_text(encoding="utf-8")
    for worker in ("| 1 |", "| 2 |", "| 4 |", "| 8 |"):
        if worker not in parallel_text:
            raise AssertionError(f"missing worker ladder entry {worker} in parallel benchmark report")
    if "0.0%" not in parallel_text:
        raise AssertionError("parallel benchmark report does not show zero failure rate")
    if "## Blocked PDKs" not in parallel_text or "ihp_sg13g2" not in parallel_text:
        raise AssertionError("parallel benchmark report does not include blocked PDK section")
    record("parallel_benchmark", True, "worker ladder and zero failure rate verified")

    node_report = args.root / "node_scaling" / "node_scaling_report.md"
    if not node_report.exists():
        raise FileNotFoundError(node_report)
    for needle in ("## Agreement", "Ranking agreement", "Verdict agreement", "Reference Summary"):
        require_contains(node_report, needle)
    record("node_scaling", True, "agreement sections present")

    env_check = args.root / "ops_plan_v1_env_check.json"
    if not env_check.exists():
        raise FileNotFoundError(env_check)
    env_loaded = json.loads(env_check.read_text(encoding="utf-8"))
    if not isinstance(env_loaded, dict) or "checks" not in env_loaded:
        raise AssertionError("env preflight output malformed")
    for entry in env_loaded.get("checks", []):
        if not bool(entry.get("ok", False)):
            raise AssertionError(f"env preflight contains failing check: {entry}")
    record("env_preflight", True, "all preflight checks passed")

    evidence_pack = args.root / "research_evidence_pack.md"
    if not evidence_pack.exists():
        raise FileNotFoundError(evidence_pack)
    evidence_text = evidence_pack.read_text(encoding="utf-8")
    for needle in ("Runnable Gate B snapshot: `4/4` pass", "Open-source runtime coverage: `4/5 PDK`", "Ops Plan v1 summary"):
        if needle not in evidence_text:
            raise AssertionError(f"missing '{needle}' in evidence pack")
    record("research_evidence_pack", True, "summary highlights verified")

    docs_pointer = REPO_ROOT / "docs" / "ops_plan_v1_latest.md"
    if not docs_pointer.exists():
        raise FileNotFoundError(docs_pointer)
    docs_text = docs_pointer.read_text(encoding="utf-8")
    if str(args.root / "ops_plan_v1_summary.md").replace("\\", "/") not in docs_text.replace("\\", "/"):
        raise AssertionError("docs pointer does not reference latest Ops Plan v1 summary")
    record("docs_pointer", True, "latest docs pointer verified")

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps({"checks": checks}, indent=2), encoding="utf-8")
    print(f"[ok] wrote: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
