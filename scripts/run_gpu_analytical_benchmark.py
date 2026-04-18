"""Compatibility wrapper for the analytical benchmark suite."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.cases import parse_cases
from benchmarks.reports import write_markdown, write_results_csv
from benchmarks.runner import run_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the compatibility analytical benchmark wrapper")
    parser.add_argument("--cases", default="10000x512,5000x1024,20000x512")
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument("--latency-mode", default="batch")
    parser.add_argument("--out-csv", type=Path, default=REPO_ROOT / "reports" / "gpu_analytical_benchmark.csv")
    parser.add_argument("--out-report", type=Path, default=REPO_ROOT / "reports" / "gpu_analytical_benchmark.md")
    args = parser.parse_args()

    result = run_suite(
        suite="full",
        device_mode="auto",
        seed=int(args.seed),
        latency_mode=str(args.latency_mode),
        cases=parse_cases(str(args.cases)),
    )
    write_results_csv(args.out_csv, result.rows)
    write_markdown(args.out_report, result.report_text)
    print(f"[ok] wrote csv: {args.out_csv}")
    print(f"[ok] wrote report: {args.out_report}")
    print(f"[ok] wrote artifact: {result.artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
