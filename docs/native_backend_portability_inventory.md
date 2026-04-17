# Native Backend Portability Inventory

This inventory focuses on the non-benchmark native/runtime path that is now partially aligned with the new backend abstraction, but not fully migrated.

## Scope

- `native_backend.py`
- `_sram_native` integration assumptions
- native sources under `native/`

## Current State

### What Is Already Aligned

- shared runtime capability inventory now comes from `backends/registry.py`
- shared torch accelerator/device helpers now come from `backends/torch_portable.py`
- GPU/native/python fallback metadata now shares a common capability-reporting shape in `_exec`
- `execution_policy.py` and the benchmark path no longer own separate accelerator detection logic

### What Still Remains In `native_backend.py`

- torch fallback math kernels for simulate/lifetime/optimize
- operation-specific native dispatch sequencing
- native-extension dispatch mixed with CPU/python fallback policy
- backend labeling and response normalization that are still local to the module

## Python-Level Portability Hotspots

- torch fallback kernels still live inside `native_backend.py`
- PyTorch ROCm compatibility still depends on device-resolution behavior rather than a distinct ROCm runtime lane
- the module still exposes operation-specific runtime entrypoints rather than a fully factored runtime backend package

## Native Extension Portability Hotspots

### `_sram_native`

- compiled binary is platform-specific and currently distributed as a local optional artifact
- no HIP/ROCm build flow is present in the repository
- no backend-neutral ABI layer exists between Python orchestration and GPU kernels

### `native/rust_core`

- current Rust native code is organized around simulation/reliability/optimizer responsibilities, but there is no ROCm/HIP integration story in the checked-in build metadata
- future GPU portability work still needs an explicit decision on whether GPU logic belongs in Rust, C++, or remains in torch-level fallbacks

### `native/cpp_eda_bridge`

- bridge code is currently about EDA/native interop rather than a backend-neutral GPU portability layer
- any future HIP-aware native acceleration would need a separate build and dependency strategy

## Recommended Migration Order

1. Keep the analytical benchmark path as the reference portability architecture.
2. Continue moving torch fallback kernels out of `native_backend.py` into shared backend modules.
3. Separate native-extension dispatch from torch GPU fallback logic.
4. Define whether future HIP work targets:
   - torch ROCm fallbacks only
   - native extension GPU kernels
   - both
5. Only then introduce a native portability branch or milestone.

## Risk Notes

- Native backend portability is broader and riskier than the analytical benchmark path.
- Without AMD hardware, only inventory and code-structure preparation are responsible deliverables.
- Any claim stronger than "inventory completed" would overstate what has been verified.
