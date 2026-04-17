"""Shared helpers for benchmark test modules."""

from __future__ import annotations

import atexit
import tempfile
from pathlib import Path

from benchmarks.runner import SuiteResult, run_suite


_RESULT_CACHE: dict[str, SuiteResult] = {}
_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []


def _cleanup_tempdirs() -> None:
    for tempdir in _TEMP_DIRS:
        tempdir.cleanup()


atexit.register(_cleanup_tempdirs)


def get_smoke_result(device_mode: str = "cpu") -> SuiteResult:
    key = str(device_mode)
    if key not in _RESULT_CACHE:
        tempdir = tempfile.TemporaryDirectory(prefix=f"sram-bench-{key}-")
        _TEMP_DIRS.append(tempdir)
        _RESULT_CACHE[key] = run_suite(
            suite="smoke",
            device_mode=key,
            artifact_root=Path(tempdir.name),
            seed=20260310,
        )
    return _RESULT_CACHE[key]
