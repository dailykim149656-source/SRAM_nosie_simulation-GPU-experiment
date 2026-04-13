# Public Scripts

Only the public-facing helper scripts are included in this repository snapshot.

## Included

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
- `run_gpu_analytical_benchmark.py` requires optional PyTorch + CUDA only for the GPU lane; CPU lanes remain runnable without it.
- `check_ops_plan_v1_env.py` is the reproducibility preflight for Ops Plan v1.
