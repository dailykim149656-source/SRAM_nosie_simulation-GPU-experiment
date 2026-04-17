# Backend Portability

The analytical benchmark path is organized so that vendor-specific code is isolated and the upper benchmark runner consumes backend metadata rather than hard-coding CUDA behavior.

## Backend Layout

- `backends/cpu_existing.py`
  - Baseline CPU dataset generation and legacy perceptron inference
- `backends/cpu_numpy.py`
  - Chunked CPU dataset generation and explicit NumPy forward path
- `backends/torch_portable.py`
  - Device-neutral PyTorch helpers
  - Holds tensor export and tensor forward logic without assuming a single vendor
- `backends/cuda_lane.py`
  - CUDA-specific availability detection
  - CUDA device naming and synchronization
  - CUDA lane execution wrapper
- `backends/registry.py`
  - Capability inventory exposed to the benchmark runner
  - Runtime capability inventory also used by `native_backend.py`

## Why This Matters

- The benchmark runner no longer reaches into CUDA-specific checks directly.
- CUDA-only responsibilities live in one place.
- The PyTorch math path is separate from the CUDA availability wrapper.
- Future work can add a ROCm-compatible lane by extending the registry and the PyTorch device-selection layer instead of rewriting the entire runner.

## Execution Policy Interaction

- `execution_policy.select_engine(...)` keeps the same public signature.
- For the analytical benchmark problem kind, it now consults backend capability state so the GPU decision reflects actual lane availability.
- `native_backend.py` now also consumes shared runtime capability metadata and shared torch accelerator/device helpers instead of owning all CUDA detection logic directly.
- CPU-only tasks still return a CPU engine even on machines with a GPU.

## Current Portability Claim

What is true today:

- CPU execution is first-class.
- NVIDIA CUDA execution is supported when PyTorch CUDA is available.
- CUDA-specific touch points are isolated to reduce future porting cost.

What is not claimed:

- No AMD ROCm benchmark results are included.
- No HIP port is implemented in this P0 batch.
- No native backend HIP migration is completed.
