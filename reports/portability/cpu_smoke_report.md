# SRAM Analytical Benchmark Report

- Suite: `smoke`
- Device mode: `cpu`
- Seed: `20260310`
- Warmup / repeats: `0` / `1`
- Selected artifact files: `metadata.json, results.csv, report.md, fidelity.md`

## Environment

- Python: `3.11.9`
- Platform: `Windows-10-10.0.26200-SP0`
- Torch: `2.6.0+cu124`
- CUDA: `NVIDIA GeForce RTX 4060 Ti`

## Results

| Case | Lane | Status | Engine | Device | Median Wall Clock (s) | Throughput (samples/s) | Mean Prediction |
|---|---|---|---|---|---:|---:|---:|
| 1024x64 | cpu_existing | pass | cpu | cpu | 0.019536 | 52414.979 | 0.059017 |
| 1024x64 | cpu_numpy | pass | cpu | cpu | 0.025163 | 40693.862 | 0.059017 |
| 1024x64 | gpu_pytorch | skipped | cpu | device_mode_cpu | 0.000000 | 0.000 | 0.000000 |

## Fidelity Summary

| Pair | Status | Max Abs Delta | Mean Abs Delta | Threshold Max | Threshold Mean |
|---|---|---:|---:|---:|---:|
| cpu_existing_vs_cpu_numpy | pass | 0.000000e+00 | 0.000000e+00 | 1.000000e-06 | 1.000000e-07 |
| cpu_existing_vs_gpu_pytorch | skipped | 0.000000e+00 | 0.000000e+00 | 1.000000e-03 | 1.000000e-04 |

## Notes

- `cpu_existing` uses `AnalyticalSRAMModel.generate_dataset()` with the fitted perceptron `.predict()` path.
- `cpu_numpy` uses chunked analytical generation plus explicit NumPy forward.
- `gpu_pytorch` is optional and records `skipped` when CUDA-capable PyTorch is unavailable or when the suite is forced to CPU mode.
