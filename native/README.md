# Native Hybrid Architecture Skeleton

This folder contains a split-native backend design:

- `rust_core/`: numerical kernels (`simulate`, `reliability`, `optimizer`)
- `cpp_eda_bridge/`: C++ bridge for external EDA integration
- `../execution_policy.py`: CPU/GPU auto-dispatch policy

## Python Integration

The Python entrypoint is `native_backend.py`, which:

1. Tries to call the Rust Python module `_sram_native`
2. Falls back to existing pure-Python modules when native is unavailable
3. In `compute_mode="auto"`, uses policy-based CPU/GPU selection
4. If GPU is unavailable, automatically falls back to CPU

Request knobs:

- `compute_mode`: `auto | cpu | gpu` (default: `auto`)
- `latency_mode`: `interactive | batch` (default: `interactive`)

For CPU-only forcing regardless of policy, set:

```bash
SRAM_FORCE_CPU=1
```

## Build Notes (Rust Python module)

Build `_sram_native` from `native/rust_core` with your preferred tooling.

Examples:

```bash
cd native/rust_core
cargo build --release
```

For Python import as extension module, use your standard PyO3 workflow
(for example, maturin or setuptools-rust).

Windows + Python 3.13 note:

```powershell
$env:PYO3_PYTHON="C:\path\to\.venv\Scripts\python.exe"
$env:PYO3_USE_ABI3_FORWARD_COMPATIBILITY="1"
cargo build --release
Copy-Item -Force target\release\_sram_native.dll ..\..\_sram_native.pyd
```

Use the project venv Python (`.venv\Scripts\python.exe`) for runtime checks,
not the Windows Store alias Python.

## Hybrid Fidelity Regression

To compare strict native hybrid against the Python hybrid reference:

```powershell
.\.venv\Scripts\python.exe .\native_hybrid_fidelity_check.py
```

Adjust thresholds or repetitions if needed:

```powershell
.\.venv\Scripts\python.exe .\native_hybrid_fidelity_check.py --repeats 30 --ber-delta-max 0.18
```

## Build Notes (C++ bridge)

```bash
cd native/cpp_eda_bridge
cmake -S . -B build
cmake --build build --config Release
```

If you already built a Rust static/shared library, pass its path:

```bash
cmake -S . -B build -DSRAM_RUST_CORE_LIB=/path/to/rust_core_library
```
