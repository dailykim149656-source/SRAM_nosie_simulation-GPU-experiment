# HIPify Preflight Inventory

This is the concrete preflight list to review before any future HIPify or manual ROCm conversion work.

## Python-Level Touch Points

- `backends/accelerator_lane.py`
- `backends/cuda_lane.py` compatibility shim
- `backends/torch_portable.py`
- `backends/runtime_torch_kernels.py`
- `execution_policy.py`
- `native_backend.py`

## Native-Level Touch Points

- `_sram_native`
- `native/` sources and build metadata

## Automatic Conversion Candidates

- direct `torch.cuda.*` spellings
- hard-coded `"cuda"` device strings
- legacy `gpu_pytorch` naming in compatibility readers

## Manual Review Required

- synchronization semantics on ROCm
- artifact claim wording after measured validation
- native build strategy for any future HIP-aware extension work
- whether runtime fallback code should stay torch-only or gain native ROCm kernels later
