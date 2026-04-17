# Limitations And Claims

This repository is explicit about what is validated today and what remains future work.

## Validated Today

- CPU analytical benchmark smoke execution via `python -m benchmarks.cli --suite smoke --device cpu`
- Standard analytical benchmark artifacts:
  - `metadata.json`
  - `results.csv`
  - `report.md`
  - `fidelity.md`
- Compatibility wrapper behavior for `scripts/run_gpu_analytical_benchmark.py`
- CPU fidelity parity between the legacy inference path and the NumPy manual-forward path
- CUDA lane skip handling when CUDA-capable PyTorch is unavailable or intentionally disabled

## Supported But Conditional

- CUDA analytical benchmark execution through the PyTorch CUDA path
- This depends on a working PyTorch CUDA install on the local machine

## Not Validated In This Batch

- AMD GPU or ROCm runtime execution
- HIPIFY output
- Native backend porting to HIP
- End-to-end migration of `native_backend.py` simulate/lifetime/optimize flows into the new backend package
- Multi-node or distributed benchmark orchestration

## Path Hygiene Scope

- Newly generated portability benchmark artifacts do not include absolute local filesystem paths.
- Newly added portability documents also avoid absolute local paths.
- Legacy public report snapshots are retained as historical artifacts and may still reflect older path hygiene.

## Safe External Claim

Use language like this:

> The repository provides reproducible CPU benchmark artifacts today, optional NVIDIA CUDA benchmark support when PyTorch CUDA is available, and isolates CUDA-specific logic to reduce future ROCm/HIP porting cost.

Avoid language like this:

- “fully portable to AMD GPUs”
- “ROCm-ready and validated”
- “HIP support complete”
