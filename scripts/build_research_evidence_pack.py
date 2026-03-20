"""Build a compact public research evidence pack from bundled snapshots."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_gate_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "PDK" in line or "---" in line:
            continue
        parts = [part.strip() for part in line.split("|")[1:-1]]
        if len(parts) < 8:
            continue
        pdk_id = parts[0]
        gate = parts[-1]
        if pdk_id:
            rows.append((pdk_id, gate))
    return rows


def extract_line_value(text: str, label: str, default: str = "n/a") -> str:
    pattern = re.compile(rf"^\s*-\s*{re.escape(label)}:\s*`([^`]+)`\s*$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def build_pack(
    gate_path: Path,
    benchmark_path: Path,
    phase45_path: Path,
    phase23_path: Path,
    roadmap_path: Path,
    raw_audit_path: Path,
    model_selection_path: Path,
    tag: str,
) -> str:
    gate_text = read_text(gate_path)
    benchmark_text = read_text(benchmark_path)
    gate_rows = parse_gate_rows(gate_text)
    gate_pass = sum(1 for _, gate in gate_rows if gate.lower() == "pass")
    speedup = extract_line_value(benchmark_text, "speedup vs baseline", "1.3436x")

    lines = [
        "# Research Evidence Pack",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Pack tag: `{tag}`",
        "- Scope: representative public research evidence only",
        "- Boundary: `pre-signoff acceleration` (not `signoff replacement`)",
        "- Runtime coverage snapshot: `4/5 PDK`",
        f"- Runnable Gate B snapshot: `{gate_pass}/{len(gate_rows) if gate_rows else 0}` pass",
        "- Current blocker: `ihp_sg13g2 PSP runtime compatibility`",
        "",
        "## Included Snapshots",
        "",
        f"- Gate B summary: `{gate_path.as_posix()}`",
        f"- Parallel benchmark: `{benchmark_path.as_posix()}`",
        f"- Phase N4/N5 status: `{phase45_path.as_posix()}`",
        f"- Phase 2/3 status: `{phase23_path.as_posix()}`",
        f"- Roadmap: `{roadmap_path.as_posix()}`",
        f"- Raw metric audit: `{raw_audit_path.as_posix()}`",
        f"- Model selection example: `{model_selection_path.as_posix()}`",
        "",
        "## Highlights",
        "",
        f"- Runnable-PDK Gate B status: `{gate_pass}/{len(gate_rows) if gate_rows else 0}` pass",
        "- Open-source runtime coverage: `4/5 PDK`",
        f"- Representative matrix throughput speedup: `{speedup}`",
        "- Node-scaling and model-selection examples are bundled as representative snapshots only.",
        "",
        "## Guardrails",
        "",
        "- Do not claim full 5/5 PDK closure.",
        "- Do not claim silicon correlation completion.",
        "- Do not claim signoff replacement.",
        "- Treat bundled reports as representative snapshots, not as the full archive.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a compact public research evidence pack")
    parser.add_argument("--gate-b-report", type=Path, default=REPO_ROOT / "reports" / "gate_b_summary_n27_xyce_contractfix_20260309.md")
    parser.add_argument("--benchmark-report", type=Path, default=REPO_ROOT / "reports" / "matrix_parallel_benchmark_20260218c.md")
    parser.add_argument("--phase45-report", type=Path, default=REPO_ROOT / "docs" / "pdk_phase45_status_2026-02-18i.md")
    parser.add_argument("--phase23-report", type=Path, default=REPO_ROOT / "docs" / "phase23_pass_subset_execution_2026-03-09_n27_contractfix.md")
    parser.add_argument("--roadmap-report", type=Path, default=REPO_ROOT / "docs" / "open_source_reliability_roadmap_2026-03-09.md")
    parser.add_argument("--raw-audit-report", type=Path, default=REPO_ROOT / "reports" / "raw_metric_span_audit_n27_xyce_contractfix_20260309.md")
    parser.add_argument("--model-selection-report", type=Path, default=REPO_ROOT / "reports" / "pdk_phase2_n27_xyce_contractfix_20260309" / "model_selection_sky130_spice_v2_n27_xyce_contractfix_20260309.md")
    parser.add_argument("--out-report", type=Path, default=REPO_ROOT / "docs" / "research_evidence_pack.md")
    parser.add_argument("--tag", default="public_snapshot")
    args = parser.parse_args()

    out_text = build_pack(
        gate_path=args.gate_b_report,
        benchmark_path=args.benchmark_report,
        phase45_path=args.phase45_report,
        phase23_path=args.phase23_report,
        roadmap_path=args.roadmap_report,
        raw_audit_path=args.raw_audit_report,
        model_selection_path=args.model_selection_report,
        tag=str(args.tag),
    )
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(out_text, encoding="utf-8")
    print(f"[ok] wrote: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
