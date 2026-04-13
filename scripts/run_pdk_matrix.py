"""Run multi-PDK full-PVT correlation matrix.

This wrapper executes `spice_validation/run_spice_validation.py` in PDK mode
for multiple PDK IDs and writes an aggregate pass/fail summary.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDK_IDS = ("sky130", "gf180mcu", "freepdk45_openram", "ihp_sg13g2", "asap7")
RUNTIME_CODE_PATTERN = re.compile(r"\[SPICE_RUNTIME:([A-Z0-9_]+)\]")

BLOCKER_RECOMMENDATIONS = {
    "NGSPICE_UNSUPPORTED_PSP": (
        "PSP model unsupported in current ngspice build. "
        "Run this PDK with Spectre/HSPICE (or compatible PSP-capable flow)."
    ),
    "NGSPICE_UNSUPPORTED_LEVEL72": (
        "BSIM-CMG level 72 unsupported in current ngspice build. "
        "Run this PDK with Spectre/HSPICE or a simulator build that supports level 72."
    ),
}


def parse_pdk_ids(text: str) -> list[str]:
    ids: list[str] = []
    for token in str(text).split(","):
        pdk_id = token.strip().lower()
        if not pdk_id:
            continue
        ids.append(pdk_id)
    if not ids:
        raise ValueError("at least one pdk id is required")
    return ids


def parse_config_overrides(entries: list[str]) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for entry in entries:
        token = str(entry).strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"invalid --config-override '{entry}' (expected pdk_id=path)")
        pdk_id, path_text = token.split("=", 1)
        pdk_key = pdk_id.strip().lower()
        if not pdk_key:
            raise ValueError(f"invalid --config-override '{entry}' (missing pdk_id)")
        overrides[pdk_key] = Path(path_text.strip()).resolve()
    return overrides


def tail_text(text: str, max_lines: int = 25, max_chars: int = 1600) -> str:
    lines = [line for line in str(text).splitlines() if line.strip()]
    if not lines:
        return ""
    clipped = "\n".join(lines[-max_lines:])
    return clipped[-max_chars:]


def classify_failure(error_text: str) -> tuple[str, str, str]:
    text = str(error_text or "")
    match = RUNTIME_CODE_PATTERN.search(text)
    runtime_code = match.group(1) if match else ""
    if runtime_code in BLOCKER_RECOMMENDATIONS:
        return "blocked", runtime_code, BLOCKER_RECOMMENDATIONS[runtime_code]
    if runtime_code:
        return "fail", runtime_code, "Inspect error details and netlist/model include paths."
    return "fail", "", "Inspect error details and netlist/model include paths."


def run_single_pdk(
    *,
    python_bin: Path,
    runner: Path,
    config_dir: Path,
    config_overrides: dict[str, Path],
    pdk_id: str,
    tag: str,
    timeout_sec: int,
    max_workers: int,
    allow_contract_fallback: bool,
    out_root: Path | None,
) -> dict[str, str]:
    config_path = config_overrides.get(pdk_id, config_dir / f"{pdk_id}.json")
    if out_root is None:
        out_csv = REPO_ROOT / "spice_validation" / "results" / f"spice_vs_native_pdk_{pdk_id}_{tag}.csv"
        out_report = REPO_ROOT / "spice_validation" / "reports" / f"spice_correlation_pdk_{pdk_id}_{tag}.md"
        raw_dir = REPO_ROOT / "spice_validation" / "results" / f"raw_{pdk_id}_{tag}"
    else:
        out_csv = out_root / "results" / f"spice_vs_native_pdk_{pdk_id}_{tag}.csv"
        out_report = out_root / "reports" / f"spice_correlation_pdk_{pdk_id}_{tag}.md"
        raw_dir = out_root / "raw" / f"{pdk_id}_{tag}"

    if not config_path.exists():
        return {
            "pdk_id": pdk_id,
            "status": "fail",
            "exit_code": "config-missing",
            "elapsed_sec": "0.000",
            "blocker_code": "CONFIG_MISSING",
            "recommendation": "Provide spice_validation/configs/pdk_runs/<pdk>.json before matrix run.",
            "out_csv": out_csv.as_posix(),
            "out_report": out_report.as_posix(),
            "error": f"missing config: {config_path.as_posix()}",
        }

    cmd = [
        str(python_bin),
        str(runner),
        "--spice-source",
        "pdk",
        "--pdk-id",
        pdk_id,
        "--pdk-config",
        str(config_path),
        "--max-workers",
        str(max(int(max_workers), 1)),
        "--raw-dir",
        str(raw_dir),
        "--out-csv",
        str(out_csv),
        "--out-report",
        str(out_report),
    ]
    if allow_contract_fallback:
        cmd.append("--allow-contract-fallback")

    started = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=max(int(timeout_sec), 1),
    )
    elapsed = time.perf_counter() - started

    if completed.returncode == 0:
        return {
            "pdk_id": pdk_id,
            "status": "pass",
            "exit_code": str(completed.returncode),
            "elapsed_sec": f"{elapsed:.3f}",
            "blocker_code": "",
            "recommendation": "",
            "out_csv": out_csv.as_posix(),
            "out_report": out_report.as_posix(),
            "error": "",
        }

    error_text = tail_text(completed.stderr or completed.stdout)
    status, blocker_code, recommendation = classify_failure(error_text)
    return {
        "pdk_id": pdk_id,
        "status": status,
        "exit_code": str(completed.returncode),
        "elapsed_sec": f"{elapsed:.3f}",
        "blocker_code": blocker_code,
        "recommendation": recommendation,
        "out_csv": out_csv.as_posix(),
        "out_report": out_report.as_posix(),
        "error": error_text,
    }


def write_summary_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary_report(path: Path, rows: list[dict[str, str]], tag: str) -> None:
    passed = sum(1 for row in rows if row["status"] == "pass")
    blocked = sum(1 for row in rows if row["status"] == "blocked")
    hard_failed = sum(1 for row in rows if row["status"] == "fail")

    lines: list[str] = [
        "# PDK Matrix Summary",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Tag: `{tag}`",
        f"- Total: `{len(rows)}`",
        f"- Passed: `{passed}`",
        f"- Blocked: `{blocked}`",
        f"- Hard Failed: `{hard_failed}`",
        "",
        "| PDK | Status | Blocker | Exit | Elapsed (s) | CSV | Report |",
        "|---|---|---|---:|---:|---|---|",
    ]

    for row in rows:
        lines.append(
            "| "
            f"{row['pdk_id']} | {row['status']} | {row['blocker_code']} | {row['exit_code']} | {row['elapsed_sec']} | "
            f"`{row['out_csv']}` | `{row['out_report']}` |"
        )

    failed_rows = [row for row in rows if row["status"] != "pass"]
    if failed_rows:
        lines.extend(["", "## Non-Pass Details", ""])
        for row in failed_rows:
            lines.append(f"### {row['pdk_id']}")
            lines.append("")
            if row["recommendation"]:
                lines.append(f"- Recommendation: {row['recommendation']}")
                lines.append("")
            lines.append("```text")
            lines.append(row["error"] or "(no error text captured)")
            lines.append("```")
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full-PVT matrix for multiple PDKs")
    parser.add_argument("--pdk-ids", default=",".join(DEFAULT_PDK_IDS))
    parser.add_argument("--tag", default="matrix_fullpvt")
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="treat blocked runtime-compatibility rows as non-fatal",
    )
    parser.add_argument(
        "--allow-contract-fallback",
        action="store_true",
        help="allow contract source fallback inside run_spice_validation.py",
    )
    parser.add_argument("--python-bin", type=Path, default=REPO_ROOT / ".venv" / "Scripts" / "python.exe")
    parser.add_argument(
        "--runner",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "run_spice_validation.py",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "configs" / "pdk_runs",
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "reports" / "pdk_matrix_summary.csv",
    )
    parser.add_argument(
        "--summary-report",
        type=Path,
        default=REPO_ROOT / "spice_validation" / "reports" / "pdk_matrix_summary.md",
    )
    parser.add_argument(
        "--config-override",
        action="append",
        default=[],
        help="per-PDK config override in the form pdk_id=absolute_or_relative_path",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=None,
        help="optional root directory for per-PDK csv/report/raw outputs",
    )
    args = parser.parse_args()

    pdk_ids = parse_pdk_ids(args.pdk_ids)
    python_bin = args.python_bin.resolve()
    runner = args.runner.resolve()
    config_dir = args.config_dir.resolve()
    config_overrides = parse_config_overrides(list(args.config_override))
    for pdk_id, path in list(config_overrides.items()):
        if not path.is_absolute():
            config_overrides[pdk_id] = (REPO_ROOT / path).resolve()

    if not python_bin.exists():
        raise FileNotFoundError(f"python binary not found: {python_bin}")
    if not runner.exists():
        raise FileNotFoundError(f"runner not found: {runner}")
    if not config_dir.exists():
        raise FileNotFoundError(f"config dir not found: {config_dir}")

    rows: list[dict[str, str]] = []
    for pdk_id in pdk_ids:
        print(f"[run] {pdk_id}")
        result = run_single_pdk(
            python_bin=python_bin,
            runner=runner,
            config_dir=config_dir,
            config_overrides=config_overrides,
            pdk_id=pdk_id,
            tag=args.tag,
            timeout_sec=args.timeout_sec,
            max_workers=args.max_workers,
            allow_contract_fallback=bool(args.allow_contract_fallback),
            out_root=args.out_root.resolve() if args.out_root is not None else None,
        )
        rows.append(result)
        print(f"[{result['status']}] {pdk_id} ({result['elapsed_sec']} s)")
        if args.stop_on_fail and result["status"] == "fail":
            break


    write_summary_csv(args.summary_csv, rows)
    write_summary_report(args.summary_report, rows, args.tag)

    print(f"[ok] summary csv: {args.summary_csv}")
    print(f"[ok] summary report: {args.summary_report}")
    hard_fail = any(row["status"] == "fail" for row in rows)
    blocked = any(row["status"] == "blocked" for row in rows)
    if hard_fail:
        return 1
    if blocked and not args.allow_blocked:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
