# Benchmark Methodology

This repository now treats the analytical SRAM benchmark as a reproducible engineering asset rather than a one-off script.

## Suites

- `smoke`
  - Purpose: CPU-only CI and quick local verification
  - Default case: `1024x64`
  - Default warmup / repeats: `0 / 1`
- `full`
  - Purpose: larger local benchmark runs
  - Default cases:
    - `10000x512`
    - `5000x1024`
    - `20000x512`
  - Default warmup / repeats: `1 / 3`

## Lanes

- `cpu_existing`
  - Uses `AnalyticalSRAMModel.generate_dataset()`
  - Uses the fitted perceptron `.predict()` path
- `cpu_numpy`
  - Uses chunked analytical dataset generation
  - Uses explicit NumPy forward on exported perceptron weights
- `gpu_pytorch`
  - Uses the PyTorch dataset/inference path on CUDA
  - Records `skipped` when CUDA-capable PyTorch is unavailable or when the suite is forced to CPU mode

## Timing Rules

- Warmup runs are excluded from reported statistics.
- Reported `wall_clock_sec` is the median of measured repeats.
- Additional timing fields record mean, standard deviation, and p95.
- Throughput is computed from the median wall-clock value.

## Fidelity Rules

- Fidelity is measured on a shared feature matrix, not on per-lane generated inputs.
- This isolates inference-path drift from dataset-sampling differences.
- Current smoke checks:
  - `cpu_existing` vs `cpu_numpy`
  - `cpu_existing` vs `gpu_pytorch` when CUDA is available
- Thresholds:
  - CPU existing vs CPU NumPy:
    - max abs delta `<= 1e-6`
    - mean abs delta `<= 1e-7`
  - CPU existing vs GPU PyTorch:
    - max abs delta `<= 1e-3`
    - mean abs delta `<= 1e-4`

## Standard Artifacts

Each run writes:

- `metadata.json`
- `results.csv`
- `report.md`
- `fidelity.md`
- optional `plots/*.png` when Matplotlib is available

The default artifact root is `artifacts/benchmarks/`.

## Commands

- CPU smoke:
  - `python -m benchmarks.cli --suite smoke --device cpu`
- Auto device selection:
  - `python -m benchmarks.cli --suite smoke --device auto`
- Alternate module entrypoint:
  - `python -m benchmarks.run_suite --suite smoke --device auto`
- Artifact schema validation:
  - `python -m benchmarks.validate --artifact-dir artifacts/benchmarks/<run_id>`
- Compatibility wrapper:
  - `python scripts/run_gpu_analytical_benchmark.py`

## Manual CUDA Validation Workflow

When a CUDA-capable PyTorch install is available:

1. Run `python -m benchmarks.cli --suite smoke --device auto`
2. Run `python -m benchmarks.validate --artifact-dir artifacts/benchmarks/<run_id>`
3. Confirm the `gpu_pytorch` row is `pass` rather than `skipped`
4. Inspect `fidelity.md` for the CPU vs GPU parity thresholds
