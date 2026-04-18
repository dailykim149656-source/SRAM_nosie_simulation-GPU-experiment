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
- `backends/accelerator_lane.py`
  - Canonical accelerator-neutral analytical benchmark lane
  - Uses shared torch runtime metadata for availability, device naming, and synchronization
- `backends/cuda_lane.py`
  - Import-only compatibility shim for older imports
- `backends/registry.py`
  - Capability inventory exposed to the benchmark runner
  - Runtime capability inventory also used by `native_backend.py`

## Why This Matters

- The benchmark runner no longer reaches into CUDA-specific checks directly.
- Accelerator-specific responsibilities live in one place.
- The PyTorch math path is separate from the accelerator availability wrapper.
- Future work can add ROCm validation on top of the current lane rather than rewriting the runner.

## Execution Policy Interaction

- `execution_policy.select_engine(...)` keeps the same public signature.
- For the analytical benchmark problem kind, it now consults backend capability state so the GPU decision reflects actual lane availability.
- `native_backend.py` consumes shared runtime capability metadata and shared torch accelerator/device helpers instead of owning all accelerator detection logic directly.
- CPU-only tasks still return a CPU engine even on machines with a GPU.

## Current Portability Claim

What is true today:

- CPU execution is first-class.
- The canonical `torch_accelerated` lane is currently CUDA-validated when a compatible PyTorch build is installed.
- Accelerator-specific touch points are isolated to reduce future ROCm/HIP porting cost.

What is not claimed:

- No AMD ROCm benchmark results are included.
- ROCm validation is still pending AMD hardware access.
- No native backend HIP migration is completed.
