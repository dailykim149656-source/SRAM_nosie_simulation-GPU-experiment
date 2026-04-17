"""Build a markdown dashboard from portability benchmark artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.schema import validate_report_text


def _load_rows(results_path: Path) -> list[dict[str, str]]:
    with results_path.open("r", encoding="utf-8", newline="") as fp:
        return list(csv.DictReader(fp))


def _latest_artifacts(artifact_root: Path, limit: int) -> list[Path]:
    candidates = [path for path in artifact_root.iterdir() if path.is_dir()]
    return sorted(candidates)[-max(int(limit), 1) :]


def build_dashboard(artifact_dirs: list[Path]) -> str:
    lines = [
        "# Portability Benchmark Dashboard",
        "",
        "This dashboard summarizes representative portability benchmark artifacts produced by the standardized analytical benchmark pipeline.",
        "",
        "| Artifact | Suite | Device Mode | CPU Existing Throughput | CPU NumPy Throughput | GPU PyTorch Throughput |",
        "|---|---|---|---:|---:|---:|",
    ]
    for artifact_dir in artifact_dirs:
        metadata = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
        rows = _load_rows(artifact_dir / "results.csv")
        row_map = {row["lane"]: row for row in rows}
        lines.append(
            "| "
            f"{artifact_dir.name} | {metadata['suite']} | {metadata['device_mode']} | "
            f"{float(row_map['cpu_existing']['throughput_samples_per_sec']):.3f} | "
            f"{float(row_map['cpu_numpy']['throughput_samples_per_sec']):.3f} | "
            f"{float(row_map['gpu_pytorch']['throughput_samples_per_sec']):.3f} |"
        )
    text = "\n".join(lines) + "\n"
    validate_report_text(text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Build portability benchmark dashboard")
    parser.add_argument("--artifact-root", type=Path, default=REPO_ROOT / "artifacts" / "benchmarks")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out-report", type=Path, default=REPO_ROOT / "reports" / "portability" / "dashboard.md")
    args = parser.parse_args()

    artifact_dirs = _latest_artifacts(Path(args.artifact_root), args.limit)
    if not artifact_dirs:
        raise FileNotFoundError(f"no benchmark artifacts found under {args.artifact_root}")

    report_text = build_dashboard(artifact_dirs)
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(report_text, encoding="utf-8")
    print(f"[ok] wrote dashboard: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
