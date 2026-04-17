"""Compatibility entry point for running analytical benchmark suites."""

from __future__ import annotations

from benchmarks.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
