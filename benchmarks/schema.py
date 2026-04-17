"""Schema validation and path sanitization helpers."""

from __future__ import annotations

import re
from typing import Iterable


RESULT_ROW_KEYS = (
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

FIDELITY_KEYS = (
    "pair",
    "status",
    "threshold_max_abs_delta",
    "threshold_mean_abs_delta",
    "max_abs_delta",
    "mean_abs_delta",
)

VALID_STATUSES = {"pass", "skipped", "unsupported", "fail"}
WINDOWS_ABS_PATH_RE = re.compile(r"[A-Za-z]:[\\/]")
POSIX_ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(Users|home|tmp|var|opt|etc)/")


def contains_absolute_path(text: str) -> bool:
    target = str(text)
    return bool(WINDOWS_ABS_PATH_RE.search(target) or POSIX_ABS_PATH_RE.search(target))


def validate_metadata(metadata: dict[str, object]) -> None:
    required = {"suite", "device_mode", "seed", "artifact_files", "backend_capabilities", "cases", "env"}
    missing = required.difference(metadata.keys())
    if missing:
        raise ValueError(f"metadata missing keys: {sorted(missing)}")


def validate_result_rows(rows: Iterable[dict[str, object]]) -> None:
    for row in rows:
        missing = [key for key in RESULT_ROW_KEYS if key not in row]
        if missing:
            raise ValueError(f"result row missing keys: {missing}")
        status = str(row.get("status", ""))
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid result status: {status}")


def validate_fidelity_records(records: Iterable[dict[str, object]]) -> None:
    for record in records:
        missing = [key for key in FIDELITY_KEYS if key not in record]
        if missing:
            raise ValueError(f"fidelity record missing keys: {missing}")
        status = str(record.get("status", ""))
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid fidelity status: {status}")


def validate_report_text(text: str) -> None:
    if contains_absolute_path(text):
        raise ValueError("report contains absolute path text")
