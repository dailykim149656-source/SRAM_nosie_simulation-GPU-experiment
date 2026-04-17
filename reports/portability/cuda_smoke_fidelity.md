# SRAM Analytical Fidelity Report

- Suite: `smoke`
- Device mode: `auto`
- Seed: `20260310`

| Pair | Status | Max Abs Delta | Mean Abs Delta | RMSE | Threshold Max | Threshold Mean |
|---|---|---:|---:|---:|---:|---:|
| cpu_existing_vs_cpu_numpy | pass | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 1.000000e-06 | 1.000000e-07 |
| cpu_existing_vs_gpu_pytorch | pass | 2.746461e-08 | 7.220779e-09 | 8.964459e-09 | 1.000000e-03 | 1.000000e-04 |

## Details

- cpu_existing_vs_cpu_numpy: Common CPU feature matrix with NumPy/manual-forward parity check.
- cpu_existing_vs_gpu_pytorch: Common CPU feature matrix with CUDA PyTorch forward check.
