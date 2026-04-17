"""Verify SRAM GPU portability PRD acceptance criteria."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.schema import contains_absolute_path


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{completed.stdout}\n{completed.stderr}")
    return completed


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        return list(csv.DictReader(fp))


def _latest_artifact(root: Path) -> Path:
    candidates = [path for path in root.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"no artifacts found under {root}")
    return sorted(candidates)[-1]


def _require_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        raise AssertionError(f"missing '{needle}' in {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify portability PRD acceptance criteria")
    parser.add_argument("--out-json", type=Path, default=REPO_ROOT / "reports" / "portability" / "prd_verify.json")
    args = parser.parse_args()

    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    with tempfile.TemporaryDirectory(prefix="sram-prd-verify-") as tempdir:
        temp_root = Path(tempdir)
        smoke_root = temp_root / "artifacts_smoke"
        env = os.environ.copy()
        env["SRAM_FORCE_CPU"] = "1"
        _run(
            [sys.executable, "-m", "benchmarks.cli", "--suite", "smoke", "--artifact-root", str(smoke_root)],
            env=env,
        )
        smoke_artifact = _latest_artifact(smoke_root)
        _run([sys.executable, "-m", "benchmarks.validate", "--artifact-dir", str(smoke_artifact)])
        smoke_rows = _read_csv(smoke_artifact / "results.csv")
        gpu_smoke_rows = [row for row in smoke_rows if row["lane"] == "gpu_pytorch"]
        if len(gpu_smoke_rows) != 1 or gpu_smoke_rows[0]["status"] not in {"skipped", "unsupported"}:
            raise AssertionError("GPU lane did not degrade gracefully in forced CPU smoke")
        record("AC-1_and_AC-3", True, "CPU-only smoke passed and GPU lane degraded gracefully")

        wrapper_csv = temp_root / "wrapper.csv"
        wrapper_report = temp_root / "wrapper.md"
        existing_default_artifacts = (
            {path.name for path in (REPO_ROOT / "artifacts" / "benchmarks").iterdir() if path.is_dir()}
            if (REPO_ROOT / "artifacts" / "benchmarks").exists()
            else set()
        )
        _run(
            [
                sys.executable,
                "scripts/run_gpu_analytical_benchmark.py",
                "--cases",
                "1024x64",
                "--out-csv",
                str(wrapper_csv),
                "--out-report",
                str(wrapper_report),
            ]
        )
        if not wrapper_csv.exists() or not wrapper_report.exists():
            raise FileNotFoundError("wrapper compatibility outputs missing")
        latest_default = _latest_artifact(REPO_ROOT / "artifacts" / "benchmarks")
        if latest_default.name in existing_default_artifacts:
            raise AssertionError("wrapper run did not create a new standard artifact directory")
        _run([sys.executable, "-m", "benchmarks.validate", "--artifact-dir", str(latest_default)])
        wrapper_rows = _read_csv(latest_default / "results.csv")
        lane_names = {row["lane"] for row in wrapper_rows}
        if lane_names != {"cpu_existing", "cpu_numpy", "gpu_pytorch"}:
            raise AssertionError("wrapper artifact does not include all required benchmark lanes")
        record("AC-2_and_AC-4", True, "wrapper compatibility and standard artifact lane set verified")

        fidelity_text = (latest_default / "fidelity.md").read_text(encoding="utf-8")
        for needle in ("cpu_existing_vs_cpu_numpy", "cpu_existing_vs_gpu_pytorch", "Threshold Max", "Threshold Mean"):
            if needle not in fidelity_text:
                raise AssertionError(f"missing fidelity evidence '{needle}'")
        record("AC-5", True, "fidelity report contains pair comparisons and thresholds")

        for path in (
            wrapper_report,
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "benchmark_methodology.md",
            REPO_ROOT / "docs" / "backend_portability.md",
            REPO_ROOT / "docs" / "hip_porting_plan.md",
            REPO_ROOT / "docs" / "limitations_and_claims.md",
        ):
            if contains_absolute_path(path.read_text(encoding="utf-8")):
                raise AssertionError(f"absolute path found in {path}")
        record("AC-6", True, "new reports and docs are sanitized")

    readme = REPO_ROOT / "README.md"
    for needle in (
        "This repository is an SRAM surrogate and simulation codebase with a portability-focused analytical benchmark path.",
        "## What Is Validated",
        "## What Is Not Claimed",
        "### CPU-only benchmark smoke",
        "### Optional CUDA benchmark smoke",
        "docs/hip_porting_plan.md",
    ):
        _require_contains(readme, needle)
    record("AC-7", True, "README covers purpose, verified scope, limits, CPU/CUDA usage, and ROCm/HIP plan")

    hip_plan = REPO_ROOT / "docs" / "hip_porting_plan.md"
    for needle in (
        "CUDA Touch Point Inventory",
        "HIPIFY Candidate Areas",
        "What Automatic Conversion Will Not Solve",
        "Manual Review Required",
        "AMD hardware is not available",
    ):
        _require_contains(hip_plan, needle)
    record("AC-8", True, "HIP porting plan contains required inventory and limitation notes")

    workflow = REPO_ROOT / ".github" / "workflows" / "cpu-smoke.yml"
    for needle in (
        "python -m unittest discover -s tests -p \"test_*.py\"",
        "python -m benchmarks.cli --suite smoke",
        "python -m benchmarks.validate --artifact-dir",
        "python scripts/run_gpu_analytical_benchmark.py",
    ):
        _require_contains(workflow, needle)
    record("AC-9", True, "CI workflow covers tests, CPU smoke, artifact validation, and wrapper run")

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps({"checks": checks}, indent=2), encoding="utf-8")
    print(f"[ok] wrote: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
