# HIP Porting Plan

This document records the current CUDA touch points in the repository and the minimum work needed to make a future ROCm/HIP migration deliberate instead of ad hoc.

## Current Constraint

- AMD hardware is not available in the current environment.
- ROCm runtime validation is therefore not claimed.
- This document is an engineering inventory and migration plan, not proof of AMD execution.

## CUDA Touch Point Inventory

### Analytical Benchmark Path

- `backends/cuda_lane.py`
  - CUDA availability gate for the benchmark GPU lane
  - CUDA device-name reporting
  - `torch.cuda.synchronize()` call after GPU inference
- `backends/torch_portable.py`
  - `torch.cuda.is_available()`
  - `torch.cuda.get_device_name(0)`
  - device resolution currently prefers `"cuda"` when available
- `execution_policy.py`
  - generic GPU detection still checks `torch.cuda.is_available()`
  - optional CuPy runtime detection is CUDA-specific

### Existing Non-Ported GPU/Native Paths

- `native_backend.py`
  - hard-coded `"cuda"` device strings in torch fallback paths
  - `torch.cuda.is_available()` checks
  - `torch.cuda`-specific tensor generator and synchronization assumptions
  - many GPU helpers still assume NVIDIA CUDA rather than a generic torch device
- legacy analytical helper facade:
  - `gpu_analytical_adapter.py` itself is now only a facade, but its exported surface still serves CUDA-capable code paths through the new backend modules

## HIPIFY Candidate Areas

These are the primary code regions to run through HIP-oriented review or automated conversion first:

- `backends/cuda_lane.py`
- `backends/torch_portable.py`
- `execution_policy.py`
- `native_backend.py`
- native sources under `native/` once the Python-level benchmark path is stable enough to justify deeper porting work

## What Automatic Conversion Can Help With

- direct CUDA API spellings in C/C++ or HIP-compatible runtime wrappers
- obvious `"cuda"` device-string usage sites
- build-time search for `torch.cuda.*` calls
- initial inventory generation for manual review

## What Automatic Conversion Will Not Solve

- correctness validation on real AMD hardware
- torch backend semantics that differ between CUDA and ROCm builds
- performance parity or kernel launch behavior
- native extension build system changes
- mixed Python/native execution policy choices
- synchronization and precision-policy decisions

## Manual Review Required

- `torch.cuda.synchronize()` usage and whether a backend-neutral barrier is needed
- device-string policy in the portable torch layer
- CuPy-based detection and whether it should remain optional, be abstracted, or be removed
- native extension assumptions in `_sram_native`
- CI strategy for future ROCm validation
- numerical parity thresholds on AMD hardware

## Recommended Migration Sequence

1. Keep the analytical benchmark path as the first migration target.
2. Replace CUDA-only checks in the portable torch layer with backend-neutral device handling where possible.
3. Add a ROCm/HIP capability entry to the backend registry only after a real ROCm environment exists.
4. Validate CPU vs ROCm parity on the same shared feature matrix used by the current fidelity smoke.
5. Migrate `native_backend.py` GPU fallbacks after the benchmark path is proven stable.

## Safe External Claim

Use this wording:

> CUDA-specific paths are isolated to reduce future ROCm/HIP porting cost, but AMD hardware validation has not been performed yet.

Do not use:

- “ROCm-ready”
- “HIP-complete”
- “portable to AMD GPUs today”
