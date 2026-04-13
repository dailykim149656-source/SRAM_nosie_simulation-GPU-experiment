"""Run worker-scaling benchmark over the PDK matrix wrapper."""

from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_int_list(text: str) -> list[int]:
    values: list[int] = []
    for token in str(text).split(","):
        token = token.strip()
        if token:
            values.append(max(int(token), 1))
    if not values:
        raise ValueError("at least one integer value is required")
    return values


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    summary_rows: list[dict[str, object]],
    *,
    pdk_ids: list[str],
    blocked_pdks: list[str],
    repeats: int,
    baseline_workers: int,
) -> None:
    lines: list[str] = [
        "# Matrix Parallel Benchmark",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- PDK IDs: `{','.join(pdk_ids)}`",
        f"- Repeats: `{repeats}`",
        f"- Baseline workers: `{baseline_workers}`",
        "",
        "## Summary",
        "",
        "| workers | runs | mean sec | stdev sec | speedup vs baseline | failure rate |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            f"{row['workers']} | {row['runs']} | {float(row['mean_sec']):.6f} | {float(row['stdev_sec']):.6f} | "
            f"{float(row['speedup_vs_baseline']):.4f}x | {100.0 * float(row['failure_rate']):.1f}% |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Timing includes matrix runner startup, per-PDK execution, summary generation, and log capture.",
            "- Failure rate counts non-zero exits from the wrapped matrix run.",
            "- Blocked PDKs are excluded from this benchmark by design.",
        ]
    )
    if blocked_pdks:
        lines.extend(
            [
                "",
                "## Blocked PDKs",
                "",
                f"- Excluded from scaling benchmark: `{', '.join(blocked_pdks)}`",
                "- These remain blocker-tracking entries and are not counted in speedup figures.",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run matrix worker-scaling benchmark")
    parser.add_argument("--pdk-ids", default="gf180mcu,freepdk45_openram")
    parser.add_argument("--blocked-pdks", default="ihp_sg13g2")
    parser.add_argument("--worker-ladder", default="1,2,4,8")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--python-bin", type=Path, default=Path(sys.executable))
    parser.add_argument("--matrix-script", type=Path, default=REPO_ROOT / "scripts" / "run_pdk_matrix.py")
    parser.add_argument("--config-override", action="append", default=[])
    parser.add_argument("--allow-contract-fallback", action="store_true")
    parser.add_argument("--out-root", type=Path, default=REPO_ROOT / "reports" / "matrix_parallel_benchmark")
    parser.add_argument("--out-csv", type=Path, default=REPO_ROOT / "reports" / "matrix_parallel_benchmark.csv")
    parser.add_argument("--out-report", type=Path, default=REPO_ROOT / "reports" / "matrix_parallel_benchmark.md")
    args = parser.parse_args()

    pdk_ids = [token.strip().lower() for token in str(args.pdk_ids).split(",") if token.strip()]
    blocked_pdks = [token.strip().lower() for token in str(args.blocked_pdks).split(",") if token.strip()]
    worker_ladder = parse_int_list(args.worker_ladder)
    repeats = max(int(args.repeats), 1)

    run_rows: list[dict[str, object]] = []
    for workers in worker_ladder:
        for repeat in range(repeats):
            run_root = args.out_root / f"workers_{workers}" / f"repeat_{repeat + 1}"
            summary_csv = run_root / "pdk_matrix_summary.csv"
            summary_report = run_root / "pdk_matrix_summary.md"
            cmd = [
                str(args.python_bin),
                str(args.matrix_script),
                "--python-bin",
                str(args.python_bin),
                "--pdk-ids",
                ",".join(pdk_ids),
                "--max-workers",
                str(workers),
                "--timeout-sec",
                str(int(args.timeout_sec)),
                "--allow-blocked",
                "--summary-csv",
                str(summary_csv),
                "--summary-report",
                str(summary_report),
                "--out-root",
                str(run_root),
                "--tag",
                f"matrix_parallel_w{workers}_r{repeat + 1}",
            ]
            if args.allow_contract_fallback:
                cmd.append("--allow-contract-fallback")
            for override in args.config_override:
                cmd.extend(["--config-override", str(override)])

            started = time.perf_counter()
            completed = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                timeout=max(int(args.timeout_sec), 1) + 300,
            )
            elapsed = time.perf_counter() - started

            run_rows.append(
                {
                    "workers": workers,
                    "repeat": repeat + 1,
                    "elapsed_sec": float(elapsed),
                    "status": "pass" if completed.returncode == 0 else "fail",
                    "return_code": int(completed.returncode),
                    "stdout_tail": "\n".join((completed.stdout or "").splitlines()[-10:]),
                    "stderr_tail": "\n".join((completed.stderr or "").splitlines()[-10:]),
                    "summary_csv": str(summary_csv),
                    "summary_report": str(summary_report),
                }
            )

    baseline_candidates = [row["elapsed_sec"] for row in run_rows if int(row["workers"]) == worker_ladder[0] and str(row["status"]) == "pass"]
    baseline_mean = statistics.fmean(baseline_candidates) if baseline_candidates else 0.0

    summary_rows: list[dict[str, object]] = []
    for workers in worker_ladder:
        worker_rows = [row for row in run_rows if int(row["workers"]) == workers]
        elapsed_values = [float(row["elapsed_sec"]) for row in worker_rows]
        pass_values = [float(row["elapsed_sec"]) for row in worker_rows if str(row["status"]) == "pass"]
        mean_sec = statistics.fmean(pass_values) if pass_values else statistics.fmean(elapsed_values)
        stdev_sec = statistics.pstdev(pass_values) if len(pass_values) >= 2 else 0.0
        failure_rate = sum(1 for row in worker_rows if str(row["status"]) != "pass") / len(worker_rows)
        speedup = (baseline_mean / mean_sec) if baseline_mean > 0.0 and mean_sec > 0.0 else 0.0
        summary_rows.append(
            {
                "workers": workers,
                "runs": len(worker_rows),
                "mean_sec": float(mean_sec),
                "stdev_sec": float(stdev_sec),
                "speedup_vs_baseline": float(speedup),
                "failure_rate": float(failure_rate),
            }
        )

    write_csv(args.out_csv, run_rows)
    write_report(
        args.out_report,
        summary_rows,
        pdk_ids=pdk_ids,
        blocked_pdks=blocked_pdks,
        repeats=repeats,
        baseline_workers=worker_ladder[0],
    )
    print(f"[ok] wrote csv: {args.out_csv}")
    print(f"[ok] wrote report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
