"""Validate a benchmark artifact directory against the portability schema."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from benchmarks.schema import (
    validate_fidelity_records,
    validate_metadata,
    validate_report_text,
    validate_result_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SRAM analytical benchmark artifacts")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    metadata_path = artifact_dir / "metadata.json"
    results_path = artifact_dir / "results.csv"
    report_path = artifact_dir / "report.md"
    fidelity_path = artifact_dir / "fidelity.md"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with results_path.open("r", encoding="utf-8", newline="") as fp:
        result_rows = list(csv.DictReader(fp))

    fidelity_records: list[dict[str, object]] = []
    fidelity_text = fidelity_path.read_text(encoding="utf-8")
    for line in fidelity_text.splitlines():
        if not line.startswith("| ") or "Pair" in line or "---" in line:
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 7:
            continue
        pair, status, max_abs, mean_abs, rmse, threshold_max, threshold_mean = parts
        fidelity_records.append(
            {
                "pair": pair,
                "status": status,
                "max_abs_delta": float(max_abs),
                "mean_abs_delta": float(mean_abs),
                "rmse": float(rmse),
                "threshold_max_abs_delta": float(threshold_max),
                "threshold_mean_abs_delta": float(threshold_mean),
            }
        )

    validate_metadata(metadata)
    validate_result_rows(result_rows)
    validate_fidelity_records(fidelity_records)
    validate_report_text(report_path.read_text(encoding="utf-8"))
    validate_report_text(fidelity_text)
    print(f"[ok] validated artifact: {artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
