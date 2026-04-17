# SRAM GPU Portability And Benchmarking

This repository is an SRAM surrogate and simulation codebase with a portability-focused analytical benchmark path.

Today it provides:

- reproducible CPU benchmark artifacts
- optional NVIDIA CUDA benchmark execution when PyTorch CUDA is available
- fidelity checks between CPU inference paths and the CUDA PyTorch path
- isolation of CUDA-specific logic to reduce future ROCm/HIP porting cost

## What Is Validated

- CPU analytical benchmark smoke runs through `python -m benchmarks.cli --suite smoke --device cpu`
- the compatibility wrapper `python scripts/run_gpu_analytical_benchmark.py` still works
- analytical benchmark runs emit standard artifacts:
  - `metadata.json`
  - `results.csv`
  - `report.md`
  - `fidelity.md`
- CPU existing vs CPU NumPy inference parity is checked automatically
- GPU lanes degrade to `skipped` or `unsupported` instead of crashing when CUDA is unavailable

## What Is Not Claimed

- No AMD GPU or ROCm benchmark result is included
- No HIP port is implemented in this batch
- `native_backend.py` simulate/lifetime/optimize flows are not fully migrated into the new backend package yet

Use conservative wording:

> CPU benchmark artifacts are reproducible today, NVIDIA CUDA support is optional, and CUDA-specific logic is isolated to reduce future ROCm/HIP porting cost.

## Linux-First Quickstart

CPU-only benchmark setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-base.txt -r requirements-benchmark.txt
python -m benchmarks.cli --suite smoke --device cpu
```

Optional CUDA benchmark setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-base.txt -r requirements-benchmark.txt
# install the correct PyTorch build for your CUDA/runtime combination
python -m benchmarks.cli --suite smoke --device auto
```

## Quick Start

Create an environment and install the benchmark stack:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-base.txt -r requirements-benchmark.txt
```

If you want the older umbrella install, `requirements.txt` still installs the base, benchmark, and UI dependency sets together.

### CPU-only benchmark smoke

```powershell
python -m benchmarks.cli --suite smoke --device cpu
```

CPU-only emulation with auto selection:

```powershell
$env:SRAM_FORCE_CPU='1'
python -m benchmarks.cli --suite smoke
Remove-Item Env:SRAM_FORCE_CPU
```

### Optional CUDA benchmark smoke

Install a CUDA-capable PyTorch build for your platform first, then run:

```powershell
python -m benchmarks.cli --suite smoke --device auto
```

### Compatibility wrapper

```powershell
python scripts/run_gpu_analytical_benchmark.py
```

Alternative module entrypoint:

```powershell
python -m benchmarks.run_suite --suite smoke --device auto
```

This keeps the legacy CLI flags while also writing a standard artifact directory under `artifacts/benchmarks/`.

## Dependency Layout

- `requirements-base.txt`
  - NumPy and SciPy
- `requirements-benchmark.txt`
  - scikit-learn
  - PyTorch is documented as an optional manual install because the correct package depends on platform and CUDA version
- `requirements-ui.txt`
  - Matplotlib, Streamlit, PySide6
- `requirements-dev.txt`
  - base + benchmark development/test stack

## Benchmark Architecture

- `backends/`
  - `cpu_existing.py`
  - `cpu_numpy.py`
  - `torch_portable.py`
  - `cuda_lane.py`
  - `registry.py`
- `benchmarks/`
  - suite cases, environment capture, metrics, report writers, CLI
- `gpu_analytical_adapter.py`
  - compatibility facade for earlier analytical helper imports

The main simulation and UI entry points remain in place:

- `main.py`
- `main_advanced.py`
- `native_backend.py`
- `streamlit_app*.py`
- `pyside_sram_app_advanced.py`

## Standard Benchmark Artifacts

Each run writes a timestamped directory under `artifacts/benchmarks/` containing:

- `metadata.json`
- `results.csv`
- `report.md`
- `fidelity.md`

New portability benchmark artifacts avoid absolute local filesystem paths.

## Representative Portability Snapshots

Checked-in sanitized snapshots are available under `reports/portability/`:

- `reports/portability/cpu_smoke_report.md`
- `reports/portability/cpu_smoke_fidelity.md`
- `reports/portability/cuda_smoke_report.md`
- `reports/portability/cuda_smoke_fidelity.md`
- `reports/portability/dashboard.md`

Some generated benchmark artifacts may also include optional plots under `plots/`.

Minimal packaging metadata and console-script entrypoints are also defined in `pyproject.toml`.

Release-oriented portability automation is defined in `.github/workflows/portability-release.yml`.

## Other Entry Points

Core simulation:

```powershell
python main.py
python main_advanced.py
python hybrid_perceptron_sram.py
python adaptive_perceptron_sram.py
python reliability_model.py
python workload_model.py
```

UI:

```powershell
pip install -r requirements-ui.txt
streamlit run streamlit_app.py
streamlit run streamlit_app_advanced.py
streamlit run streamlit_app_unified.py
python pyside_sram_app_advanced.py
```

Validation and report generation:

```powershell
python spice_validation/run_spice_validation.py --spice-source placeholder
python scripts/run_pdk_matrix.py
python scripts/run_model_selection.py
python scripts/run_node_scaling.py
python scripts/build_research_evidence_pack.py
python scripts/export_research_bundle.py --tag public_snapshot --skip-zip
```

## Key Docs

- `docs/benchmark_baseline_inventory.md`
- `docs/benchmark_methodology.md`
- `docs/backend_portability.md`
- `docs/hip_porting_plan.md`
- `docs/limitations_and_claims.md`
- `docs/results_interpretation_guide.md`
- `docs/portability_issue_backlog.md`
- `docs/portability_release_checklist.md`
- `docs/prd_completion_matrix.md`
- `docs/native_backend_portability_inventory.md`
- `docs/pdk_validation_criteria.md`
- `docs/open_source_reliability_roadmap_2026-03-09.md`
- `docker/README.md`
- `reports/portability/changelog.md`
