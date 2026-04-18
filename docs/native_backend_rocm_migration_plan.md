# Native Backend ROCm Migration Plan

The native backend is not being ported to HIP in this batch. This document narrows what remains.

## Current State

- `native_backend.py` already reuses shared runtime capability metadata from `backends/registry.py`.
- torch fallbacks reuse `backends/runtime_torch_kernels.py`.
- accelerator labeling is now normalized around torch backend/runtime fields.

## Remaining Work

- move more operation-specific torch fallback formatting out of `native_backend.py`
- decide whether future ROCm work stays torch-level or adds native kernels
- define build and packaging strategy for any HIP-aware native extension path

## Explicit Non-Goals

- no HIP build system
- no AMD-measured native runtime results
- no claim that `_sram_native` is portable to ROCm today
