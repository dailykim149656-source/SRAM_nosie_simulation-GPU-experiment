# Limitations And Claims

This repository is explicit about what is validated today and what remains future work.

## Validated Today

- CPU analytical benchmark smoke execution via `python -m benchmarks.cli --suite smoke --device cpu`
- Standard analytical benchmark artifacts:
  - `metadata.json`
  - `results.csv`
  - `report.md`
  - `fidelity.md`
- fresh artifact metadata records validation scope, claim level, and accelerator runtime fields
- compatibility wrapper behavior for `scripts/run_gpu_analytical_benchmark.py`
- CPU fidelity parity between the legacy inference path and the NumPy manual-forward path
- accelerator lane skip handling when a compatible runtime is unavailable or intentionally disabled

## Supported But Conditional

- the canonical `torch_accelerated` analytical lane
- in the current repository state, this is only CUDA-validated and depends on a working PyTorch CUDA install on the local machine

## Not Validated In This Batch

- AMD GPU or ROCm runtime execution
- HIPIFY output
- native backend porting to HIP
- end-to-end migration of `native_backend.py` simulate/lifetime/optimize flows into the new backend package
- multi-node or distributed benchmark orchestration

## Path Hygiene Scope

- newly generated portability benchmark artifacts do not include absolute local filesystem paths
- newly added portability documents also avoid absolute local paths
- legacy public report snapshots are retained as historical artifacts and may still reflect older path hygiene

## Safe External Claim

Use language like this:

> The repository provides reproducible CPU benchmark artifacts today, a canonical `torch_accelerated` lane that is currently CUDA-validated when a compatible PyTorch build is available, and isolates accelerator-specific logic to reduce future ROCm/HIP porting cost.

Avoid language like this:

- `fully portable to AMD GPUs`
- `ROCm-ready and validated`
- `HIP support complete`
