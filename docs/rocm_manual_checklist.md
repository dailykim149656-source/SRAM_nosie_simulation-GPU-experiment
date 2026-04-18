# ROCm Manual Checklist

Use this checklist only after AMD hardware and a Linux ROCm environment are available.

## Environment Setup

- Install ROCm on Linux.
- Install a matching PyTorch ROCm build.
- Confirm `rocminfo` and `python -c "import torch; print(torch.version.hip)"` both work.

## Benchmark Sequence

1. Run `python -m benchmarks.cli --suite smoke --device auto`.
2. Run `python -m benchmarks.validate --artifact-dir <run_id>`.
3. Inspect `report.md`, `fidelity.md`, and `metadata.json`.
4. Run `python -m benchmarks.cli --suite full --device auto` only if smoke passes.

## Required Checks

- `torch_accelerated` is `pass`.
- `backend_kind=hip` and `runtime_kind=rocm` appear in fresh artifacts.
- `cpu_existing_vs_torch_accelerated` is within thresholds.
- `validation_scope` is suitable for a real ROCm claim.

## Publication Guardrail

- Do not publish ROCm support language until measured artifacts exist.
- Do not claim native HIP support from torch-only validation.
