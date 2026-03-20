"""Export the compact public research bundle into a directory and optional zip."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAG = "public_snapshot"


def bundle_sources() -> list[Path]:
    return [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "research_evidence_pack.md",
        REPO_ROOT / "docs" / "pdk_phase45_status_2026-02-18i.md",
        REPO_ROOT / "docs" / "phase23_pass_subset_execution_2026-03-09_n27_contractfix.md",
        REPO_ROOT / "docs" / "open_source_reliability_roadmap_2026-03-09.md",
        REPO_ROOT / "reports" / "gate_b_summary_n27_xyce_contractfix_20260309.md",
        REPO_ROOT / "reports" / "matrix_parallel_benchmark_20260218c.md",
        REPO_ROOT / "reports" / "node_scaling_report_n27_xyce_20260218.md",
        REPO_ROOT / "reports" / "raw_metric_span_audit_n27_xyce_contractfix_20260309.md",
        REPO_ROOT / "reports" / "pdk_phase2_n27_xyce_contractfix_20260309" / "model_selection_sky130_spice_v2_n27_xyce_contractfix_20260309.md",
    ]


def write_manifest(path: Path, included: list[Path], missing: list[Path], tag: str) -> None:
    lines = [
        "# Research Bundle Manifest",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Tag: `{tag}`",
        f"- Included files: `{len(included)}`",
        f"- Missing files: `{len(missing)}`",
        "",
        "## Included",
        "",
    ]
    for src in included:
        lines.append(f"- `{src.relative_to(REPO_ROOT).as_posix()}`")
    if missing:
        lines.extend(["", "## Missing", ""])
        for src in missing:
            lines.append(f"- `{src.relative_to(REPO_ROOT).as_posix()}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_sources(out_dir: Path, tag: str) -> tuple[list[Path], list[Path]]:
    included: list[Path] = []
    missing: list[Path] = []
    for src in bundle_sources():
        if not src.exists():
            missing.append(src)
            continue
        rel = src.relative_to(REPO_ROOT)
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        included.append(src)
    manifest_path = out_dir / "BUNDLE_MANIFEST.md"
    write_manifest(manifest_path, included, missing, tag)
    included.append(manifest_path)
    return included, missing


def zip_bundle(out_dir: Path, zip_path: Path) -> None:
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for path in out_dir.rglob("*"):
            if path.is_dir():
                continue
            zf.write(path, arcname=path.relative_to(out_dir))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the current public research bundle")
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--out-root", type=Path, default=REPO_ROOT / "artifacts")
    parser.add_argument("--skip-zip", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_root / f"research_bundle_{args.tag}"
    zip_path = args.out_root / f"research_bundle_{args.tag}.zip"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    included, missing = copy_sources(out_dir, str(args.tag))
    if not args.skip_zip:
        zip_bundle(out_dir, zip_path)

    print(f"[ok] bundle dir: {out_dir}")
    if not args.skip_zip:
        print(f"[ok] bundle zip: {zip_path}")
    print(f"[ok] included: {len(included)}")
    print(f"[ok] missing: {len(missing)}")
    for src in missing:
        print(f"[warn] missing: {src.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
