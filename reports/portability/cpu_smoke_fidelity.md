# SRAM Analytical Fidelity Report

- Suite: `smoke`
- Device mode: `cpu`
- Seed: `20260310`

| Pair | Status | Max Abs Delta | Mean Abs Delta | RMSE | Threshold Max | Threshold Mean |
|---|---|---:|---:|---:|---:|---:|
| cpu_existing_vs_cpu_numpy | pass | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 1.000000e-06 | 1.000000e-07 |
| cpu_existing_vs_gpu_pytorch | skipped | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 1.000000e-03 | 1.000000e-04 |

## Details

- cpu_existing_vs_cpu_numpy: Common CPU feature matrix with NumPy/manual-forward parity check.
- cpu_existing_vs_gpu_pytorch: GPU fidelity skipped: device_mode_cpu.
