"""Generate a portability changelog from the current repository evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.schema import validate_report_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate portability changelog")
    parser.add_argument(
        "--verify-json",
        type=Path,
        default=REPO_ROOT / "reports" / "portability" / "prd_verify.json",
    )
    parser.add_argument(
        "--completion-matrix",
        type=Path,
        default=REPO_ROOT / "docs" / "prd_completion_matrix.md",
    )
    parser.add_argument(
        "--out-report",
        type=Path,
        default=REPO_ROOT / "reports" / "portability" / "changelog.md",
    )
    args = parser.parse_args()

    verify_payload = json.loads(args.verify_json.read_text(encoding="utf-8"))
    checks = verify_payload.get("checks", [])
    passed = [entry for entry in checks if bool(entry.get("ok", False))]
    matrix_text = args.completion_matrix.read_text(encoding="utf-8")

    lines = [
        "# Portability Changelog",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Acceptance checks passing: `{len(passed)}/{len(checks)}`",
        "",
        "## Validation Highlights",
        "",
    ]
    for entry in passed:
        lines.append(f"- `{entry['name']}`: {entry['detail']}")

    lines.extend(
        [
            "",
            "## Repository Deliverables",
            "",
            "- Backend abstraction and runtime capability inventory are present.",
            "- Benchmark CLI, validator, dashboard, and portability snapshots are present.",
            "- CPU-only CI and wrapper compatibility checks are present.",
            "- Documentation covers methodology, portability limits, HIP plan, release checklist, and completion matrix.",
            "",
            "## Traceability Source",
            "",
            f"- Completion matrix: `{args.completion_matrix.name}`",
            "",
            "## Matrix Excerpt",
            "",
        ]
    )
    for line in matrix_text.splitlines()[:14]:
        lines.append(line)

    text = "\n".join(lines) + "\n"
    validate_report_text(text)
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(text, encoding="utf-8")
    print(f"[ok] wrote changelog: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
