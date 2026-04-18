"""Validate a benchmark artifact directory against the portability schema."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from benchmarks.schema import (
    CANONICAL_ACCELERATOR_LANE,
    EXTENDED_CAPABILITY_KEYS,
    EXTENDED_ENV_KEYS,
    EXTENDED_METADATA_KEYS,
    EXTENDED_RESULT_ROW_KEYS,
    LEGACY_ACCELERATOR_LANE,
    VALID_CLAIM_LEVELS,
    VALID_VALIDATION_SCOPES,
    artifact_uses_extended_schema,
    normalize_lane_name,
    validate_fidelity_records,
    validate_metadata,
    validate_report_text,
    validate_result_rows,
)


def _parse_fidelity_markdown(fidelity_text: str) -> list[dict[str, object]]:
    fidelity_records: list[dict[str, object]] = []
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
    return fidelity_records


def _missing_keys(payload: dict[str, object], keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if key not in payload]


def _validate_extended_artifact(metadata: dict[str, object], result_rows: list[dict[str, object]]) -> None:
    if not artifact_uses_extended_schema(metadata, result_rows):
        return

    missing_metadata_keys = _missing_keys(metadata, EXTENDED_METADATA_KEYS)
    if missing_metadata_keys:
        raise ValueError(f"fresh artifact missing top-level extended metadata keys: {missing_metadata_keys}")

    validation_scope = str(metadata.get("validation_scope", ""))
    if validation_scope not in VALID_VALIDATION_SCOPES:
        raise ValueError(f"invalid validation_scope: {validation_scope}")

    claim_level = str(metadata.get("claim_level", ""))
    if claim_level not in VALID_CLAIM_LEVELS:
        raise ValueError(f"invalid claim_level: {claim_level}")

    env = metadata.get("env")
    if not isinstance(env, dict):
        raise ValueError("fresh artifact env payload must be a JSON object")
    missing_env_keys = _missing_keys(env, EXTENDED_ENV_KEYS)
    if missing_env_keys:
        raise ValueError(f"fresh artifact env missing extended keys: {missing_env_keys}")

    capabilities = metadata.get("backend_capabilities")
    if not isinstance(capabilities, list):
        raise ValueError("fresh artifact backend_capabilities must be a list")
    raw_capability_names: list[str] = []
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            raise ValueError(f"fresh artifact capability[{index}] must be an object")
        missing_capability_keys = _missing_keys(capability, EXTENDED_CAPABILITY_KEYS)
        if missing_capability_keys:
            raise ValueError(
                f"fresh artifact capability[{index}] missing extended keys: {missing_capability_keys}"
            )
        raw_capability_names.append(str(capability.get("name", "")))

    if LEGACY_ACCELERATOR_LANE in raw_capability_names:
        raise ValueError(
            "fresh artifact must use canonical accelerator capability name "
            f"'{CANONICAL_ACCELERATOR_LANE}', not legacy alias '{LEGACY_ACCELERATOR_LANE}'"
        )

    normalized_capability_names = {normalize_lane_name(name) for name in raw_capability_names}
    if CANONICAL_ACCELERATOR_LANE not in normalized_capability_names:
        raise ValueError(f"fresh artifact missing canonical accelerator capability '{CANONICAL_ACCELERATOR_LANE}'")

    raw_lane_names: list[str] = []
    for index, row in enumerate(result_rows):
        missing_row_keys = [key for key in EXTENDED_RESULT_ROW_KEYS if key not in row]
        if missing_row_keys:
            raise ValueError(f"fresh artifact row[{index}] missing extended keys: {missing_row_keys}")
        raw_lane_names.append(str(row.get("lane", "")))

    if LEGACY_ACCELERATOR_LANE in raw_lane_names:
        raise ValueError(
            "fresh artifact must record canonical lane "
            f"'{CANONICAL_ACCELERATOR_LANE}', not legacy alias '{LEGACY_ACCELERATOR_LANE}'"
        )

    normalized_lane_names = {normalize_lane_name(name) for name in raw_lane_names}
    if CANONICAL_ACCELERATOR_LANE not in normalized_lane_names:
        raise ValueError(f"fresh artifact missing canonical lane '{CANONICAL_ACCELERATOR_LANE}'")


def validate_artifact_dir(artifact_dir: Path) -> None:
    metadata_path = artifact_dir / "metadata.json"
    results_path = artifact_dir / "results.csv"
    report_path = artifact_dir / "report.md"
    fidelity_path = artifact_dir / "fidelity.md"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with results_path.open("r", encoding="utf-8", newline="") as fp:
        result_rows = list(csv.DictReader(fp))

    fidelity_text = fidelity_path.read_text(encoding="utf-8")
    fidelity_records = _parse_fidelity_markdown(fidelity_text)

    validate_metadata(metadata)
    validate_result_rows(result_rows)
    _validate_extended_artifact(metadata, result_rows)
    validate_fidelity_records(fidelity_records)
    validate_report_text(report_path.read_text(encoding="utf-8"))
    validate_report_text(fidelity_text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SRAM analytical benchmark artifacts")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    validate_artifact_dir(artifact_dir)
    print(f"[ok] validated artifact: {artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
