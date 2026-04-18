# Public Scripts

Only the public-facing helper scripts are included in this repository snapshot.

## Included

- `python -m benchmarks.cli`
- `python -m benchmarks.validate`
- `scripts/build_portability_dashboard.py`
- `scripts/generate_portability_changelog.py`
- `scripts/verify_portability_prd.py`
- `scripts/run_pdk_matrix.py`
- `scripts/run_matrix_parallel_benchmark.py`
- `scripts/run_model_selection.py`
- `scripts/run_raw_metric_audit.py`
- `scripts/run_node_scaling.py`
- `scripts/run_gpu_analytical_benchmark.py`
- `scripts/run_ops_plan_v1.py`
- `scripts/build_research_evidence_pack.py`
- `scripts/check_ops_plan_v1_env.py`
- `scripts/verify_ops_plan_v1_outputs.py`
- `scripts/setup_ops_plan_v1_windows.ps1`
- `scripts/export_research_bundle.py`

## Usage

```powershell
python -m benchmarks.cli --suite smoke --device cpu
python -m benchmarks.run_suite --suite smoke --device auto
python -m benchmarks.validate --artifact-dir artifacts/benchmarks/<run_id>
python scripts/build_portability_dashboard.py
python scripts/generate_portability_changelog.py
python scripts/verify_portability_prd.py
python scripts/run_pdk_matrix.py
python scripts/run_matrix_parallel_benchmark.py
python scripts/run_model_selection.py
python scripts/run_raw_metric_audit.py
python scripts/run_node_scaling.py
python scripts/run_gpu_analytical_benchmark.py
python scripts/run_ops_plan_v1.py
python scripts/build_research_evidence_pack.py
python scripts/check_ops_plan_v1_env.py
python scripts/verify_ops_plan_v1_outputs.py --root reports/ops_plan_v1/<tag> --out-json reports/ops_plan_v1_verify.json
python scripts/export_research_bundle.py --tag public_snapshot --skip-zip
```

Windows full setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_ops_plan_v1_windows.ps1
```

Latest run pointer:

- `docs/ops_plan_v1_latest.md`

## Notes

- Internal experimental helpers and bulk archival scripts are intentionally not included in this public snapshot.
- The evidence pack and exported research bundle operate only on the representative artifacts that are bundled here.
- `run_gpu_analytical_benchmark.py` is now a compatibility wrapper over `python -m benchmarks.cli`.
- `python -m benchmarks.validate` validates a generated portability benchmark artifact directory.
- `build_portability_dashboard.py` builds a markdown summary over recent portability benchmark artifacts.
- `generate_portability_changelog.py` writes a sanitized portability changelog from the current evidence set.
- `verify_portability_prd.py` checks the portability PRD acceptance criteria end to end.
- In CI or local smoke checks, prefer writing wrapper CSV/Markdown outputs under `artifacts/` or another disposable path if you do not want working-tree report files.
- The canonical accelerator lane is `torch_accelerated`; it is currently CUDA-validated when a compatible PyTorch build is installed, while ROCm validation is still pending.
- `check_ops_plan_v1_env.py` is the reproducibility preflight for Ops Plan v1 and now reports generic torch accelerator/runtime readiness instead of CUDA-only labels.
- `verify_ops_plan_v1_outputs.py` accepts both historical `gpu_pytorch` rows and canonical `torch_accelerated` rows by normalizing lane aliases during verification.
- `.github/workflows/portability-release.yml` automates release-time verification, changelog generation, and evidence publishing on `portability-v*` tags.
