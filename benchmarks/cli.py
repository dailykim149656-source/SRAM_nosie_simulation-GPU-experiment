"""CLI entry point for the analytical benchmark suite."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks.runner import run_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SRAM analytical benchmark suites")
    parser.add_argument("--suite", default="smoke", choices=("smoke", "full"))
    parser.add_argument("--device", dest="device_mode", default="auto", choices=("auto", "cpu", "gpu"))
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument("--latency-mode", default="batch")
    parser.add_argument("--cases", default=None, help="override suite cases, e.g. 10000x512,5000x1024")
    parser.add_argument("--warmup-runs", type=int, default=None)
    parser.add_argument("--repeat-runs", type=int, default=None)
    args = parser.parse_args()

    result = run_suite(
        suite=str(args.suite),
        device_mode=str(args.device_mode),
        artifact_root=args.artifact_root,
        seed=int(args.seed),
        latency_mode=str(args.latency_mode),
        case_text=args.cases,
        warmup_runs=args.warmup_runs,
        repeat_runs=args.repeat_runs,
    )
    print(f"[ok] wrote artifact: {result.artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
