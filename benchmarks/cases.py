"""Benchmark case definitions and parsing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    n_samples: int
    variability_samples: int


SMOKE_CASES = (
    BenchmarkCase(case_id="1024x64", n_samples=1024, variability_samples=64),
)

FULL_CASES = (
    BenchmarkCase(case_id="10000x512", n_samples=10000, variability_samples=512),
    BenchmarkCase(case_id="5000x1024", n_samples=5000, variability_samples=1024),
    BenchmarkCase(case_id="20000x512", n_samples=20000, variability_samples=512),
)


def parse_cases(case_text: str) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for token in str(case_text).split(","):
        text = token.strip()
        if not text:
            continue
        left, right = text.lower().split("x", 1)
        cases.append(
            BenchmarkCase(
                case_id=f"{int(left)}x{int(right)}",
                n_samples=int(left),
                variability_samples=int(right),
            )
        )
    if not cases:
        raise ValueError("at least one benchmark case is required")
    return cases


def get_suite_cases(suite: str) -> list[BenchmarkCase]:
    suite_key = str(suite).strip().lower() or "smoke"
    if suite_key == "smoke":
        return list(SMOKE_CASES)
    if suite_key == "full":
        return list(FULL_CASES)
    raise ValueError(f"unsupported suite: {suite}")
