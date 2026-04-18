"""Schema validation and path sanitization helpers."""

from __future__ import annotations

import re
from typing import Iterable


BASE_RESULT_ROW_KEYS = (
    "case_id",
    "lane",
    "status",
    "selected_engine",
    "selection_reason",
    "work_size",
    "gpu_detected",
    "device_name",
    "wall_clock_sec",
    "throughput_samples_per_sec",
    "mean_prediction",
)

EXTENDED_RESULT_ROW_KEYS = (
    "device_display_name",
    "backend_kind",
    "runtime_kind",
)

EXTENDED_METADATA_KEYS = (
    "validation_scope",
    "claim_level",
)

EXTENDED_ENV_KEYS = (
    "torch_build_tag",
    "cuda_version",
    "hip_version",
)

EXTENDED_CAPABILITY_KEYS = (
    "backend_kind",
    "runtime_kind",
    "device_display_name",
)

FIDELITY_KEYS = (
    "pair",
    "status",
    "threshold_max_abs_delta",
    "threshold_mean_abs_delta",
    "max_abs_delta",
    "mean_abs_delta",
)

VALID_STATUSES = {"pass", "skipped", "unsupported", "fail"}
VALID_CLAIM_LEVELS = {"measured", "prepared", "planned"}
VALID_VALIDATION_SCOPES = {
    "cpu_validated",
    "cuda_validated",
    "accelerator_validated",
    "rocm_validated",
    "rocm_pending",
}
CANONICAL_ACCELERATOR_LANE = "torch_accelerated"
LEGACY_ACCELERATOR_LANE = "gpu_pytorch"
LANE_ALIASES = {
    "gpu_pytorch": "torch_accelerated",
}
FIDELITY_PAIR_ALIASES = {
    "cpu_existing_vs_gpu_pytorch": "cpu_existing_vs_torch_accelerated",
}
WINDOWS_ABS_PATH_RE = re.compile(r"[A-Za-z]:[\\/]")
POSIX_ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(Users|home|tmp|var|opt|etc)/")


def contains_absolute_path(text: str) -> bool:
    target = str(text)
    return bool(WINDOWS_ABS_PATH_RE.search(target) or POSIX_ABS_PATH_RE.search(target))


def normalize_lane_name(name: str) -> str:
    return LANE_ALIASES.get(str(name), str(name))


def normalize_fidelity_pair_name(name: str) -> str:
    return FIDELITY_PAIR_ALIASES.get(str(name), str(name))


def row_uses_extended_schema(row: dict[str, object]) -> bool:
    return any(key in row for key in EXTENDED_RESULT_ROW_KEYS)


def capability_uses_extended_schema(capability: dict[str, object]) -> bool:
    return any(key in capability for key in EXTENDED_CAPABILITY_KEYS)


def metadata_uses_extended_schema(metadata: dict[str, object]) -> bool:
    if any(key in metadata for key in EXTENDED_METADATA_KEYS):
        return True
    env = metadata.get("env")
    if isinstance(env, dict) and any(key in env for key in EXTENDED_ENV_KEYS):
        return True
    capabilities = metadata.get("backend_capabilities")
    if isinstance(capabilities, list):
        for capability in capabilities:
            if isinstance(capability, dict) and capability_uses_extended_schema(capability):
                return True
    return False


def artifact_uses_extended_schema(
    metadata: dict[str, object],
    rows: Iterable[dict[str, object]],
) -> bool:
    if metadata_uses_extended_schema(metadata):
        return True
    for row in rows:
        if row_uses_extended_schema(row):
            return True
    return False


def validate_metadata(metadata: dict[str, object]) -> None:
    required = {"suite", "device_mode", "seed", "artifact_files", "backend_capabilities", "cases", "env"}
    missing = required.difference(metadata.keys())
    if missing:
        raise ValueError(f"metadata missing keys: {sorted(missing)}")


def validate_result_rows(rows: Iterable[dict[str, object]]) -> None:
    for row in rows:
        normalized_row = dict(row)
        normalized_row["lane"] = normalize_lane_name(str(normalized_row.get("lane", "")))
        missing = [key for key in BASE_RESULT_ROW_KEYS if key not in normalized_row]
        if missing:
            raise ValueError(f"result row missing keys: {missing}")
        status = str(normalized_row.get("status", ""))
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid result status: {status}")


def validate_fidelity_records(records: Iterable[dict[str, object]]) -> None:
    for record in records:
        normalized_record = dict(record)
        normalized_record["pair"] = normalize_fidelity_pair_name(str(normalized_record.get("pair", "")))
        missing = [key for key in FIDELITY_KEYS if key not in normalized_record]
        if missing:
            raise ValueError(f"fidelity record missing keys: {missing}")
        status = str(normalized_record.get("status", ""))
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid fidelity status: {status}")


def validate_report_text(text: str) -> None:
    if contains_absolute_path(text):
        raise ValueError("report contains absolute path text")
