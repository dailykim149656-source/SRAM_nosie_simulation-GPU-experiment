# ROCm Validation Matrix

This document defines the first real AMD validation pass once compatible hardware is available.

## Scope

- Target platform: Linux only
- Target runtime family: ROCm with a PyTorch-on-ROCm build
- Current repo status: ROCm validation pending

## Validation Modes

| Mode | Purpose | Commands | Expected outcome |
|---|---|---|---|
| Smoke | verify install and artifact schema | `python -m benchmarks.cli --suite smoke --device auto` then `python -m benchmarks.validate --artifact-dir <run_id>` | `torch_accelerated` runs or fails with a diagnosable ROCm/runtime issue |
| Full | collect representative throughput and fidelity | `python -m benchmarks.cli --suite full --device auto` | comparable artifacts with canonical lane and fidelity records |

## Acceptance Gates

- PyTorch reports a ROCm/HIP build and the accelerator lane resolves successfully.
- `results.csv` contains `torch_accelerated` with `status=pass`.
- `fidelity.md` includes `cpu_existing_vs_torch_accelerated`.
- `validation_scope` can truthfully move from `cpu_validated` or `cuda_validated` to `rocm_validated`.
- No README or report text claims ROCm validation until these checks complete.

## Blocked States

- ROCm tools missing.
- PyTorch installed without ROCm support.
- `torch_accelerated` remains `skipped` or `unsupported`.
- Numerical parity fails the existing thresholds.

## Recording Rules

- Do not rewrite historical CUDA artifacts.
- Publish ROCm artifacts as fresh benchmark runs.
- Update public wording only after measured artifacts exist.
