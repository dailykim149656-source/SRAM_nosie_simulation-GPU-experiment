# Results Interpretation Guide

Use the portability benchmark artifacts to answer three questions separately.

## 1. Did The Run Complete Reliably?

Check `results.csv` and `report.md`.

- `pass`
  - the lane executed and produced timing and prediction statistics
- `skipped`
  - the lane was intentionally not run in the current environment or mode
- `unsupported`
  - the environment or policy does not support the lane as requested
- `fail`
  - the lane ran but violated a validation contract

Do not treat `skipped` as a benchmark failure by itself. For this repository, graceful skip behavior is expected when accelerator support is unavailable.

## 2. Are The Numbers Comparable?

Check `fidelity.md`.

- `cpu_existing_vs_cpu_numpy`
  - validates the legacy CPU inference path against the explicit NumPy forward path
- `cpu_existing_vs_torch_accelerated`
  - validates the CPU reference against the canonical accelerator lane when available

Interpretation:

- low max and mean absolute delta means the alternate lane is numerically consistent with the CPU reference
- a `skipped` accelerator fidelity row means the environment did not provide a usable accelerator lane
- a `fail` fidelity row means performance numbers should not be trusted until the numerical mismatch is explained
- historical artifacts may use the legacy pair name `cpu_existing_vs_gpu_pytorch`; current readers normalize it to `cpu_existing_vs_torch_accelerated`

## 3. What Does The Timing Mean?

Check `wall_clock_sec`, `wall_clock_sec_mean`, `wall_clock_sec_std`, `wall_clock_sec_p95`, and `throughput_samples_per_sec`.

- `wall_clock_sec`
  - median runtime of measured repeats
- `wall_clock_sec_std`
  - repeat-to-repeat variability
- `throughput_samples_per_sec`
  - coarse throughput for the benchmark case

Use the median for comparison first. Use the standard deviation and p95 to judge stability.

## Recommended Review Order

1. Confirm the lane status is acceptable.
2. Confirm fidelity status is acceptable.
3. Compare median wall-clock and throughput values.
4. Read environment metadata before drawing conclusions across machines.

## Safe Public Narrative

Good summary:

> The CPU baseline and alternate lanes were exercised under a standardized artifact schema, and fidelity checks were used to confirm whether performance comparisons are numerically meaningful.

Bad summary:

- `GPU is faster, therefore the port is correct`
- `Skipped GPU lane means the benchmark failed`
- `One CUDA run proves ROCm portability`
