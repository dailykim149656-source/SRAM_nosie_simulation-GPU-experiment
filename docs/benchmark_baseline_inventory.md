# Benchmark Baseline Inventory

This document freezes the analytical benchmark baseline that existed before the portability refactor.

## Baseline Checks

- Date captured: `2026-04-17`
- Regression suite: `python -m unittest tests.test_regressions`
- Observed result at capture time: `11 tests, OK`
- Legacy benchmark entrypoint: `scripts/run_gpu_analytical_benchmark.py`

## Legacy Analytical Benchmark Shape

- Input flags:
  - `--cases`
  - `--seed`
  - `--latency-mode`
  - `--out-csv`
  - `--out-report`
- Lanes:
  - `cpu_existing`
  - `cpu_numpy`
  - `gpu_pytorch`
- Legacy CSV columns:
  - `case_id`
  - `lane`
  - `status`
  - `selected_engine`
  - `selection_reason`
  - `work_size`
  - `gpu_detected`
  - `device_name`
  - `wall_clock_sec`
  - `throughput_samples_per_sec`
  - `mean_prediction`

## Compatibility Decisions

- The wrapper script keeps the same public flags.
- The wrapper continues to emit a CSV and Markdown report at caller-provided paths.
- The wrapper now also writes a standard benchmark artifact directory under `artifacts/benchmarks/<run_id>/`.
- Fresh artifacts use the canonical lane name `torch_accelerated`, while readers still normalize the historical `gpu_pytorch` alias.

## Known Pre-P0 Gaps

- No dedicated backend package for the analytical benchmark path.
- No standard `metadata.json` or `fidelity.md` artifact.
- No CPU-only CI lane for the analytical benchmark path.
- Existing public snapshots may still contain absolute paths from older report pipelines. New portability benchmark artifacts do not.
