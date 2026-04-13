"""Recompute raw metric span audit for Ops Plan v1."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spice_validation.run_spice_validation import (  # noqa: E402
    CONTRACT_RAW_MIN_SPAN_BY_METRIC,
    safe_float,
)


RAW_METRICS = (
    ("spice_snm_mv_raw", "native_snm_mv"),
    ("spice_hold_snm_mv_raw", "native_hold_snm_mv"),
    ("spice_read_snm_mv_raw", "native_read_snm_mv"),
    ("spice_write_margin_mv_raw", "native_write_margin_mv"),
)


def collect_csv_paths(csv_paths: list[Path], input_globs: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for path in csv_paths:
        if path.exists():
            resolved.append(path.resolve())
    for pattern in input_globs:
        resolved.extend(sorted(REPO_ROOT.glob(pattern)))
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in resolved:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def derive_pdk_id(rows: list[dict[str, str]], csv_path: Path) -> str:
    if rows and str(rows[0].get("pdk_id", "")).strip():
        return str(rows[0]["pdk_id"]).strip().lower()
    stem = csv_path.stem.lower()
    marker = "spice_vs_native_pdk_"
    if marker in stem:
        remainder = stem.split(marker, 1)[1]
        return remainder.split("_", 1)[0]
    return csv_path.stem.lower()


def load_grouped_rows(paths: list[Path]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as fp:
            rows = list(csv.DictReader(fp))
        if not rows:
            continue
        pdk_id = derive_pdk_id(rows, path)
        grouped.setdefault(pdk_id, []).extend(rows)
    return grouped


def finite_values(rows: list[dict[str, str]], key: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        value = safe_float(row.get(key), default=float("nan"))
        if math.isfinite(value):
            out.append(value)
    return out


def metric_stats(rows: list[dict[str, str]], spice_key: str, native_key: str) -> dict[str, float | int | str]:
    spice_values = finite_values(rows, spice_key)
    native_values = finite_values(rows, native_key)
    if not spice_values:
        return {
            "finite_count": 0,
            "min": float("nan"),
            "max": float("nan"),
            "span": 0.0,
            "mean": float("nan"),
            "median": float("nan"),
            "native_span": 0.0,
            "span_ratio": float("nan"),
            "status": "missing",
        }

    spice_sorted = sorted(spice_values)
    span = float(spice_sorted[-1] - spice_sorted[0]) if len(spice_sorted) >= 2 else 0.0
    native_span = float(max(native_values) - min(native_values)) if len(native_values) >= 2 else 0.0
    span_ratio = (span / native_span) if native_span > 1e-12 else float("nan")
    metric_name = spice_key.replace("spice_", "").replace("_raw", "")
    min_span = float(CONTRACT_RAW_MIN_SPAN_BY_METRIC.get(metric_name, 0.0))
    status = "usable" if span >= min_span and len(spice_values) >= 2 else "degenerate"
    median_index = len(spice_sorted) // 2
    if len(spice_sorted) % 2 == 0:
        median_value = (spice_sorted[median_index - 1] + spice_sorted[median_index]) / 2.0
    else:
        median_value = spice_sorted[median_index]

    return {
        "finite_count": len(spice_values),
        "min": float(spice_sorted[0]),
        "max": float(spice_sorted[-1]),
        "span": span,
        "mean": float(sum(spice_values) / len(spice_values)),
        "median": float(median_value),
        "native_span": native_span,
        "span_ratio": span_ratio,
        "status": status,
    }


def suggested_primary_source(stats_by_metric: dict[str, dict[str, float | int | str]]) -> str:
    primary = stats_by_metric["spice_snm_mv_raw"]
    read = stats_by_metric["spice_read_snm_mv_raw"]
    if str(primary["status"]) != "usable" and str(read["status"]) == "usable":
        return "spice_read_snm_mv_raw"
    return "spice_snm_mv_raw"


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float) -> str:
    if math.isfinite(float(value)):
        return f"{float(value):.6f}"
    return "n/a"


def write_report(
    path: Path,
    grouped_rows: dict[str, list[dict[str, str]]],
    summary_rows: list[dict[str, object]],
    input_label: str,
) -> None:
    lines: list[str] = [
        "# Raw Metric Span Audit",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Input tag: `{input_label}`",
        f"- PDKs: `{', '.join(summary['pdk_id'] for summary in summary_rows)}`",
        "- Metrics: `spice_snm_mv_raw, spice_hold_snm_mv_raw, spice_read_snm_mv_raw, spice_write_margin_mv_raw`",
        "- Status rule: `degenerate` means raw span is below the configured minimum threshold for that metric.",
        "",
        "## Summary",
        "",
        "| PDK | Primary SNM Raw Span | Read SNM Raw Span | Primary Status | Read Status | Suggested Primary Source |",
        "|---|---:|---:|---|---|---|",
    ]

    for row in summary_rows:
        lines.append(
            "| "
            f"{row['pdk_id']} | {fmt(float(row['primary_span']))} | {fmt(float(row['read_span']))} | "
            f"{row['primary_status']} | {row['read_status']} | {row['suggested_primary_source']} |"
        )

    for summary in summary_rows:
        pdk_id = str(summary["pdk_id"])
        rows = grouped_rows[pdk_id]
        lines.extend(["", f"## {pdk_id}", ""])
        lines.extend(
            [
                "| Metric | Finite Rows | Min | Max | Span | Mean | Median | Native Span | Span Ratio vs Native | Status |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        stats_by_metric = summary["stats_by_metric"]
        assert isinstance(stats_by_metric, dict)
        for spice_key, _ in RAW_METRICS:
            item = stats_by_metric[spice_key]
            assert isinstance(item, dict)
            lines.append(
                "| "
                f"{spice_key} | {int(item['finite_count'])} | {fmt(float(item['min']))} | {fmt(float(item['max']))} | "
                f"{fmt(float(item['span']))} | {fmt(float(item['mean']))} | {fmt(float(item['median']))} | "
                f"{fmt(float(item['native_span']))} | {fmt(float(item['span_ratio']))} | {item['status']} |"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute raw metric span audit")
    parser.add_argument("--csv-path", type=Path, action="append", default=[])
    parser.add_argument(
        "--input-glob",
        action="append",
        default=[],
        help="glob relative to repo root, e.g. reports/ops_plan_v1/tag/results/*.csv",
    )
    parser.add_argument("--tag", default="ops_plan_v1")
    parser.add_argument("--out-report", type=Path, default=REPO_ROOT / "reports" / "raw_metric_audit.md")
    parser.add_argument("--out-csv", type=Path, default=REPO_ROOT / "reports" / "raw_metric_audit.csv")
    args = parser.parse_args()

    input_globs = list(args.input_glob) if args.input_glob else ["spice_validation/results/spice_vs_native_pdk_*.csv"]
    csv_paths = collect_csv_paths(list(args.csv_path), input_globs)
    if not csv_paths:
        raise FileNotFoundError("no csv inputs found for raw metric audit")

    grouped = load_grouped_rows(csv_paths)
    if not grouped:
        raise RuntimeError("no non-empty csv datasets found for raw metric audit")

    summary_rows: list[dict[str, object]] = []
    flat_rows: list[dict[str, object]] = []
    for pdk_id in sorted(grouped):
        stats_by_metric: dict[str, dict[str, float | int | str]] = {}
        for spice_key, native_key in RAW_METRICS:
            stats = metric_stats(grouped[pdk_id], spice_key, native_key)
            stats_by_metric[spice_key] = stats
            flat_rows.append(
                {
                    "pdk_id": pdk_id,
                    "metric": spice_key,
                    **stats,
                }
            )

        summary_rows.append(
            {
                "pdk_id": pdk_id,
                "primary_span": stats_by_metric["spice_snm_mv_raw"]["span"],
                "read_span": stats_by_metric["spice_read_snm_mv_raw"]["span"],
                "primary_status": stats_by_metric["spice_snm_mv_raw"]["status"],
                "read_status": stats_by_metric["spice_read_snm_mv_raw"]["status"],
                "suggested_primary_source": suggested_primary_source(stats_by_metric),
                "stats_by_metric": stats_by_metric,
            }
        )

    write_summary_csv(
        args.out_csv,
        [
            {key: value for key, value in row.items() if key != "stats_by_metric"}
            for row in summary_rows
        ],
    )
    write_report(
        args.out_report,
        grouped_rows=grouped,
        summary_rows=summary_rows,
        input_label=str(args.tag),
    )
    print(f"[ok] wrote csv: {args.out_csv}")
    print(f"[ok] wrote report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
