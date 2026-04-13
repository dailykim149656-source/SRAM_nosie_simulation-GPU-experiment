"""Preflight checks for Ops Plan v1 runtime prerequisites."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def check_python_module(name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(name)
        return True, "ok"
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Ops Plan v1 environment")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "configs" / "ops_plan_v1.json")
    parser.add_argument("--out-json", type=Path, default=REPO_ROOT / "reports" / "ops_plan_v1_env_check.json")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest must be an object: {args.manifest}")

    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    for module_name in ("numpy", "scipy", "sklearn"):
        ok, detail = check_python_module(module_name)
        record(f"python_module:{module_name}", ok, detail)

    ok, detail = check_python_module("_sram_native")
    record("native_module:_sram_native", ok, detail)

    ngspice_bin = shutil.which("ngspice") or str(Path(r"C:\msys64\ucrt64\bin\ngspice.exe"))
    record("binary:ngspice", Path(ngspice_bin).exists(), ngspice_bin)

    xyce_bin = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")
    record("binary:xyce", xyce_bin.exists(), str(xyce_bin))

    available_torch, torch_detail = check_python_module("torch")
    if available_torch:
        import torch  # type: ignore

        record("python_module:torch", True, "ok")
        record("cuda:torch", bool(torch.cuda.is_available()), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cuda-unavailable")
    else:
        record("python_module:torch", False, torch_detail)
        record("cuda:torch", False, "torch-unavailable")

    pdk_run_configs = manifest.get("pdk_run_configs", {})
    if isinstance(pdk_run_configs, dict):
        for pdk_id, config_rel in pdk_run_configs.items():
            config_path = (REPO_ROOT / str(config_rel)).resolve()
            record(f"config:{pdk_id}", config_path.exists(), str(config_path))

    vendor_root = REPO_ROOT / "vendor" / "pdks"
    record("vendor:pdks_root", vendor_root.exists(), str(vendor_root))
    for subdir in ("sky130_fd_pr", "gf180mcu_fd_pr", "asap7_pdk_r1p7", "OpenRAM"):
        path = vendor_root / subdir
        record(f"vendor:{subdir}", path.exists(), str(path))

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps({"checks": checks}, indent=2), encoding="utf-8")
    print(f"[ok] wrote: {args.out_json}")
    failed = [entry for entry in checks if not bool(entry["ok"])]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
